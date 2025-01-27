import sys
import os
import math
import ogr
import osr
import argparse
import logging

from mapswipe_workers.ProjectTypes.BuildArea import TileFunctions as t


########################################################################################################################
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-i', '--input_file', required=False, default=None, type=str,
                    help='the input file containning the geometry as kml, shp or geojson')
parser.add_argument('-o', '--output_file', required=False, default=None, type=str,
                    help='the output file containning the processed groups geometries as kml, shp or geojson')
parser.add_argument('-z', '--zoomlevel', required=False, default=18, type=int,
                    help='the zoom level.')
########################################################################################################################


def get_geometry_from_file(infile):
    """
    The function to load input geometries from an .shp, .kml or .geojson file

    Parameters
    ----------
    infile : str
        the path to the .shp, .kml or .geojson file containing the input geometries

    Returns
    -------
    extent : list
        the extent of the layer as [x_min, x_max, y_min, y_max]
    geomcol : ogr.Geometry(ogr.wkbGeometryCollection)
        a geometry collection of all feature geometries for the given file
    """

    try:
        infile_name = infile.split('.')[0]
        infile_extension = infile.split('.')[-1]
    except:
        print("check input file")
        sys.exit()

    # Get the driver --> supported formats: Shapefiles, GeoJSON, kml
    if infile_extension == 'shp':
        driver = ogr.GetDriverByName('ESRI Shapefile')
    elif infile_extension == 'geojson':
        driver = ogr.GetDriverByName('GeoJSON')
    elif infile_extension == 'kml':
        driver = ogr.GetDriverByName('KML')
    else:
        print('Check input file format for ' + infile)
        print('Supported formats .shp .geojson .kml')
        sys.exit()

    datasource = driver.Open(infile, 0)
    try:
        # Get the data layer
        layer = datasource.GetLayer()
    except:
        print('Error, please check input file!')
        print('## ' + infile)
        sys.exit()

    # get feature geometry of all features of the input file
    geomcol = ogr.Geometry(ogr.wkbGeometryCollection)
    for feature in layer:
        geomcol.AddGeometry(feature.GetGeometryRef())

    extent = layer.GetExtent()
    logging.info('got geometry and extent from file')
    return extent, geomcol


def get_horizontal_slice(extent, geomcol, zoom):
    """
    The function slices all input geometries vertically using a height of max 3 tiles per geometry. The function iterates over all input geometries. For each geometry tile coordinates are calculated. Then this geometry is split into several geometries using the min and max tile coordinates for the geometry.

    Parameters
    ----------
    extent : list
        the extent of the layer as [x_min, x_max, y_min, y_max]
    geomcol : ogr.Geometry(ogr.wkbGeometryCollection)
        a geometry collection of all feature geometries for the given file
    zoom : int
        the tile map service zoom level

    Returns
    -------
    slice_infos : dict
        a dictionary containing a list of "tile_y_top" coordinates, a list of "tile_y_bottom" coordinates and a "slice_collection" containing a ogr geometry collection
    """


    logging.info('geomcol: %s' % geomcol)

    slice_infos = {
        'tile_y_top': [],
        'tile_y_bottom': [],
        'slice_collection': ogr.Geometry(ogr.wkbGeometryCollection)
    }

    xmin = extent[0]
    xmax = extent[1]
    ymin = extent[2]
    ymax = extent[3]

    # we only use the first geometry
    polygon_to_slice = geomcol.GetGeometryRef(0)
    #logging.info('polygon to slice: %s' % polygon_to_slice)

    # get upper left left tile coordinates
    pixel = t.lat_long_zoom_to_pixel_coords(ymax, xmin, zoom)
    tile = t.pixel_coords_to_tile_address(pixel.x, pixel.y)
    TileX_left = tile.x
    TileY_top = tile.y

    # get lower right tile coordinates
    pixel = t.lat_long_zoom_to_pixel_coords(ymin, xmax, zoom)
    tile = t.pixel_coords_to_tile_address(pixel.x, pixel.y)

    TileX_right = tile.x
    TileY_bottom = tile.y


    TileWidth = abs(TileX_right - TileX_left)
    TileHeight = abs(TileY_top - TileY_bottom)

    TileY = TileY_top
    TileX = TileX_left

    # get rows
    rows = int(math.ceil(TileHeight / 3))
    # get columns
    cols = int(math.ceil(TileWidth / 3))

    ############################################################

    for i in range(0, rows+1):
        # Calculate lat, lon of upper left corner of tile
        PixelX = TileX_left * 256
        PixelY = TileY * 256
        lon_left, lat_top = t.pixel_coords_zoom_to_lat_lon(PixelX, PixelY, zoom)


        PixelX = (TileX_right) * 256
        PixelY = (TileY+3) * 256
        lon_right, lat_bottom = t.pixel_coords_zoom_to_lat_lon(PixelX, PixelY, zoom)

        # Create Geometry
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(lon_left, lat_top)
        ring.AddPoint(lon_right, lat_top)
        ring.AddPoint(lon_right, lat_bottom)
        ring.AddPoint(lon_left, lat_bottom)
        ring.AddPoint(lon_left, lat_top)
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)

        sliced_poly = poly.Intersection(polygon_to_slice)

        if sliced_poly:
            if sliced_poly.GetGeometryName() == 'POLYGON':
                slice_infos['tile_y_top'].append(TileY)
                slice_infos['tile_y_bottom'].append(TileY+3)
                slice_infos['slice_collection'].AddGeometry(sliced_poly)
            elif sliced_poly.GetGeometryName() == 'MULTIPOLYGON':
                for geom_part in sliced_poly:
                    slice_infos['tile_y_top'].append(TileY)
                    slice_infos['tile_y_bottom'].append(TileY + 3)
                    slice_infos['slice_collection'].AddGeometry(geom_part)
            else:
                pass
        else:
            pass


        #####################
        TileY = TileY + 3

    return slice_infos


def get_vertical_slice(slice_infos, zoom, width_threshold=40):
    """
    The function slices the horizontal stripes vertically. Each input stripe has a height of three tiles and will be splitted into vertical parts. The width of each part is defined by the width threshold set below.

    Parameters
    ----------
    slice_infos : dict
        a dictionary containing a list of "tile_y_top" coordinates, a list of "tile_y_bottom" coordinates and a "slice_collection" containing a ogr geometry collection
    zoom : int
        the tile map service zoom level
    width_threshold :  int
        the number of vertical tiles for a group, this defines how "long" groups are.

    Returns
    -------
    raw_groups : dict
        a dictionary containing "xMin", "xMax", "yMin", "yMax" and a "group_polygon" as ogr.Geometry(ogr.wkbPolygon) and the "group_id" as key
    """

    # create an empty dict for the group ids and TileY_min, TileY_may, TileX_min, TileX_max
    raw_groups = {}
    group_id = 100

    # add these variables to test, if groups are created correctly
    TileY_top = -1

    geomcol = slice_infos['slice_collection']

    # process each polygon individually
    for p in range(0, geomcol.GetGeometryCount()):
        horizontal_slice = geomcol.GetGeometryRef(p)

        # sometimes we get really really small polygones, skip these
        if horizontal_slice.GetArea() < 0.0000001:
            continue
            logging.info('polygon area: %s' % horizontal_slice.GetArea())
            logging.info('skipped this polygon')

        extent = horizontal_slice.GetEnvelope()
        xmin = extent[0]
        xmax = extent[1]
        ymin = extent[2]
        ymax = extent[3]

        # get upper left left tile coordinates
        pixel = t.lat_long_zoom_to_pixel_coords(ymax, xmin, zoom)
        tile = t.pixel_coords_to_tile_address(pixel.x, pixel.y)
        TileX_left = tile.x

        # get lower right tile coordinates
        pixel = t.lat_long_zoom_to_pixel_coords(ymin, xmax, zoom)
        tile = t.pixel_coords_to_tile_address(pixel.x, pixel.y)
        TileX_right = tile.x


        # we don't compute tile y top and tile y botton coordinates again, but get the ones from the list
        # doing so we can avoid problems due to rounding errors and resulting in wrong tile coordinates
        TileY_top = slice_infos['tile_y_top'][p]
        TileY_bottom = slice_infos['tile_y_bottom'][p]


        TileWidth = abs(TileX_right - TileX_left)
        TileHeight = abs(TileY_top - TileY_bottom)
        TileX = TileX_left

        # get rows
        rows = int(math.ceil(TileHeight / 3))

        # get columns
        cols = int(math.ceil(TileWidth / width_threshold))
        # avoid zero division error and check if cols is smaller than zero
        if cols < 1:
            continue
        # how wide should the group be, calculate from total width and do equally for all slices
        step_size = math.ceil(TileWidth/cols)

        for i in range(0, cols):
            # we need to make sure that geometries are not clipped at the edge
            if i == (cols-1):
                step_size = TileX_right - TileX + 1

            # Calculate lat, lon of upper left corner of tile
            PixelX = TileX * 256
            PixelY = TileY_top * 256
            lon_left, lat_top = t.pixel_coords_zoom_to_lat_lon(PixelX, PixelY, zoom)
            #logging.info('lon_left: %s, lat_top: %s' % (lon_left, lat_top))

            PixelX = (TileX + step_size) * 256
            PixelY = TileY_bottom * 256
            lon_right, lat_bottom = t.pixel_coords_zoom_to_lat_lon(PixelX, PixelY, zoom)
            #logging.info('lon_right: %s, lat_bottom: %s' % (lon_right, lat_bottom))

            # Create Geometry
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(lon_left, lat_top)
            ring.AddPoint(lon_right, lat_top)
            ring.AddPoint(lon_right, lat_bottom)
            ring.AddPoint(lon_left, lat_bottom)
            ring.AddPoint(lon_left, lat_top)
            group_poly = ogr.Geometry(ogr.wkbPolygon)
            group_poly.AddGeometry(ring)

            # add info to groups_dict
            group_id += 1
            raw_groups[group_id] = {
                "xMin": str(TileX),
                "xMax": str(TileX + step_size - 1),
                "yMin": str(TileY_top),
                "yMax": str(TileY_bottom - 1),
                "group_polygon": group_poly
            }

            #####################
            TileX = TileX + step_size

    logging.info('created vertical_slice')
    return raw_groups


def extent_to_slices(infile, zoom):
    """
    The function to polygon geometries of a given input file into horizontal slices and then vertical slices.

    Parameters
    ----------
    infile : str
        the path to the .shp, .kml or .geojson file containing the input geometries
    zoom : int
        the tile map service zoom level

    Returns
    -------
    raw_groups_dict : dict
        a dictionary containing "xMin", "xMax", "yMin", "yMax" and a "group_polygon" as ogr.Geometry(ogr.wkbPolygon) and the "group_id" as key
    """
    extent, geomcol = get_geometry_from_file(infile)

    # get horizontal slices --> rows
    horizontal_slice_infos = get_horizontal_slice(extent, geomcol, zoom)
    # outfile = 'data/horizontally_sliced_groups_{}.geojson'.format(config["project_id"])
    # save_geom_as_geojson(horizontal_slice_infos['slice_collection'], outfile)

    # then get vertical slices --> columns
    raw_groups_dict = get_vertical_slice(horizontal_slice_infos, zoom)

    return raw_groups_dict


def save_geom_as_geojson(geomcol, outfile):
    """
    The function to create a geojson file from a ogr geometry collection

    Parameters
    ----------
    geomcol : ogr.Geometry(ogr.wkbGeometryCollection)
        a geometry collection of all feature geometries for the given file
    outfile : str
        the path to the .shp, .kml or .geojson file containing the input geometries

    Returns
    -------
    bool
        True if successful, False otherwise.
    """

    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)

    driver = ogr.GetDriverByName('GeoJSON')
    if os.path.exists(outfile):
        driver.DeleteDataSource(outfile)
    data_final = driver.CreateDataSource(outfile)
    layer_final = data_final.CreateLayer(outfile, wgs, geom_type=ogr.wkbPolygon)
    fdef_final = layer_final.GetLayerDefn()

    # save each polygon as feature in layer
    for p in range(0, geomcol.GetGeometryCount()):
        da = geomcol.GetGeometryRef(p)
        da.FlattenTo2D()
        if da.GetGeometryName() == 'POLYGON':
            feature_final = ogr.Feature(fdef_final)
            feature_final.SetGeometry(da)
            layer_final.CreateFeature(feature_final)
            feature_final.Destroy

        elif da.GetGeometryName() == 'MULTIPOLYGON':
            for geom_part in da:
                feature_final = ogr.Feature(fdef_final)
                feature_final.SetGeometry(geom_part)
                layer_final.CreateFeature(feature_final)
                feature_final.Destroy
        else:
            print('other geometry type: %s' % da.GetGeometryName())
            print(da)
            continue

    geomcol = None
    data_final.Destroy()

    return True


def save_slices_as_geojson(raw_group_infos, outfile):
    """
    The function to create a geojson file from the groups dictionary.

    Parameters
    ----------
    raw_group_infos : dict
        a dictionary containing "xMin", "xMax", "yMin", "yMax" and a "group_polygon" as ogr.Geometry(ogr.wkbPolygon) and the "group_id" as key
    outfile : str
        the path a .geojson file for storing the output

    Returns
    -------
    bool
        True if successful, False otherwise.
    """

    # Create the output Driver
    outDriver = ogr.GetDriverByName('GeoJSON')
    # Create the output GeoJSON
    outDataSource = outDriver.CreateDataSource(outfile)
    outLayer = outDataSource.CreateLayer(outfile, geom_type=ogr.wkbPolygon)

    outLayer.CreateField(ogr.FieldDefn('group_id', ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn('xmin', ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn('xmax', ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn('ymin', ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn('ymax', ogr.OFTInteger))

    for group_id, group in raw_group_infos.items():
        # write to geojson file
        featureDefn = outLayer.GetLayerDefn()
        outFeature = ogr.Feature(featureDefn)
        outFeature.SetGeometry(group['group_polygon'])
        outFeature.SetField('group_id', group_id)
        outFeature.SetField('xmin', group['xMin'])
        outFeature.SetField('xmax', group['xMax'])
        outFeature.SetField('ymin', group['yMin'])
        outFeature.SetField('ymax', group['yMax'])
        outLayer.CreateFeature(outFeature)
        outFeature = None

    outDataSource = None
    logging.info('created all %s.' % outfile)
    return True


########################################################################################################################
if __name__ == '__main__':

    try:
        args = parser.parse_args()
    except:
        print('have a look at the input arguments, something went wrong there.')

    slices = extent_to_slices(args.input_file, args.zoomlevel)
    save_slices_as_geojson(slices, args.output_file)