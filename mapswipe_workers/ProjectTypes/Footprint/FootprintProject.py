import os
import logging
import ogr
import urllib.request
from typing import Union

from mapswipe_workers.basic import auth
from mapswipe_workers.basic.BaseProject import BaseProject
from mapswipe_workers.ProjectTypes.Footprint.FootprintGroup import FootprintGroup
from mapswipe_workers.ProjectTypes.Footprint import GroupingFunctions as g


########################################################################################################################
# A Footprint Project
class FootprintProject(BaseProject):
    """
    The subclass for a project of the type Footprint
    """

    project_type = 2

    ####################################################################################################################
    # INIT - Existing projects from id, new projects from import_key and import_dict                                   #
    ####################################################################################################################
    def __init__(self, project_id, firebase, postgres):
        """
        The function to init a project

        Parameters
        ----------
        project_id : int
            The id of the project
        firebase : pyrebase firebase object
            initialized firebase app with admin authentication
        postgres : database connection class
            The database connection to postgres database
        import_key : str, optional
            The key of this import from firebase imports tabel
        import_dict : dict, optional
            The project information to be imported as a dictionary
        """

        super().__init__(project_id, firebase, postgres)

    ####################################################################################################################
    # EXPORT - We define a bunch of functions related to exporting exiting projects                                    #
    ####################################################################################################################

    def aggregate_results(self, postgres: object) -> dict:
        """
        The Function to aggregate results per task.

        Parameters
        ----------
        postgres : database connection class
            The database connection to postgres database

        Returns
        -------
        results_dict : dict
            result of the aggregation as dictionary. Key for every object is task id. Properties are decision,
            yes_count, maybe_count, bad_imagery_count

        """
        p_con = postgres()
        # sql command
        sql_query = '''
                    select
                      task_id as id
                      ,project_id as project
                      ,avg(cast(info ->> 'result' as integer))as decision
                      ,SUM(CASE
                        WHEN cast(info ->> 'result' as integer) = 1 THEN 1
                        ELSE 0
                       END) AS yes_count
                       ,SUM(CASE
                        WHEN cast(info ->> 'result' as integer) = 2 THEN 1
                        ELSE 0
                       END) AS maybe_count
                       ,SUM(CASE
                        WHEN cast(info ->> 'result' as integer) = 3 THEN 1
                        ELSE 0
                       END) AS bad_imagery_count
                    from
                      results
                    where
                      project_id = %s and cast(info ->> 'result' as integer) > 0
                    group by
                      task_id
                      ,project_id'''

        header = ['id', 'project_id', 'decision', 'yes_count', 'maybe_count', 'bad_imagery_count']
        data = [self.id]

        project_results = p_con.retr_query(sql_query, data)
        # delete/close db connection
        del p_con

        results_dict = {}
        for row in project_results:
            row_id = ''
            row_dict = {}
            for i in range(0, len(header)):
                # check for task id
                if header[i] == 'id':
                    row_id = str(row[i])
                elif header[i] == 'decision':  # check for float value
                    row_dict[header[i]] = float(str(row[i]))
                # check for integer value
                elif header[i] in ['yes_count', 'maybe_count', 'bad_imagery_count']:
                    row_dict[header[i]] = int(str(row[i]))
                # all other values will be handled as strings
                else:
                    row_dict[header[i]] = row[i]
            results_dict[row_id] = row_dict

        logging.warning('got results information from postgres for project: %s. rows = %s' % (self.id,
                                                                                              len(project_results)))
        return results_dict
