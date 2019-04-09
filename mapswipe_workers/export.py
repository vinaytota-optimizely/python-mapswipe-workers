import json
import os

from mapswipe_workers import auth
from mapswipe_workers.definitions import DATA_PATH
from mapswipe_workers.definitions import logger


def generate_stats():

    pg_db = auth.postgresDB()

    query_select_project_total = '''
        SELECT COUNT(*)
        FROM projects;
    '''
    query_select_project_finished = '''
        SELECT COUNT(*)
        FROM projects
        WHERE progress=100;
    '''

    query_select_project_inactive = '''
        SELECT COUNT(*)
        FROM projects
        WHERE status='inactive';
    '''

    query_select_project_active = '''
        SELECT COUNT(*)
        FROM projects
        WHERE status='active';
    '''

    query_select_project_avg_progress = '''
        SELECT AVG(progress)
        FROM projects
        WHERE progress <> 100
        AND status='active';
    '''

    query_select_user_total = '''
        SELECT COUNT(*)
        FROM users;
    '''

    query_select_user_distance_total = '''
        SELECT SUM(distance)
        FROM users;
    '''

    query_select_user_contributions_total = '''
        SELECT SUM(contribution_count)
        FROM users;
    '''

    project_total = pg_db.query(query_select_project_total)[0]
    project_finished = pg_db.query(query_select_project_finished)[0]
    project_inactive = pg_db.query(query_select_project_inactive)[0]
    project_active = pg_db.query(query_select_project_active)[0]
    project_avg_progress = pg_db.query(query_select_project_avg_progress)[0]
    user_total = pg_db.query(query_select_user_total)[0]
    user_distance_total = pg_db.query(query_select_user_distance_total)[0]
    user_contributions_total = pg_db.query(
            query_select_user_contributions_total
            )[0]

    stats = {
            'project_total': project_total,
            'project_finished': project_finished,
            'project_inactive': project_inactive,
            'project_active': project_active,
            'project_avg_progress': project_avg_progress,
            'user_total': user_total,
            'user_distance_total': user_distance_total,
            'user_contributions_total': user_contributions_total,
            }

    del(pg_db)

    logger.info('generated stats')

    return stats


def export_stats():

    if not os.path.isdir(DATA_PATH):
        os.mkdir(DATA_PATH)

    stats = generate_stats()

    stats_filename = f'{DATA_PATH}/stats.json'

    with open(stats_filename, 'w') as outfile:
        json.dump(stats, outfile)

    logger.info('exported stats')
