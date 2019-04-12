import pickle
import os

from mapswipe_workers import auth
from mapswipe_workers.definitions import DATA_PATH


def delete_sample_data_from_firebase(fb_db, project_id):
    ref = fb_db.reference(f'results/{project_id}')
    ref.set({})
    ref = fb_db.reference(f'tasks/{project_id}')
    ref.set({})
    ref = fb_db.reference(f'groups/{project_id}')
    ref.set({})
    ref = fb_db.reference(f'projects/{project_id}')
    ref.set({})
    ref = fb_db.reference(f'projectDrafts/{project_id}')
    ref.set({})
    print(
            f'Firebase: '
            f'deleted projectDraft, project, groups, tasks and results '
            f'with the project id: {project_id}'
            )


def delete_sample_results_from_postgres(pg_db, project_id):
    p_con = pg_db()
    sql_query = '''
        DELETE FROM results
        WHERE EXISTS (
            SELECT project_id
            FROM results
            WHERE project_id = %s
            );
        DELETE FROM tasks WHERE project_id = %s;
        DELETE FROM groups WHERE project_id = %s;
        DELETE FROM projects WHERE project_id = %s;

        '''

    data = [
        project_id,
        project_id,
        project_id,
        project_id,
    ]

    p_con.query(sql_query, data)
    print(
            f'Postgres: '
            f'deleted project, groups, tasks and results '
            f'with the project id: {project_id}'
            )


def delete_local_files(project_id):
    fn = f'{DATA_PATH}/results/results_{project_id}.json'
    if os.path.isfile(fn):
        os.remove(fn)
    # os.remove(
    #         f'{DATA_PATH}'
    #         f'/progress/progress_{project_id}.json'
    #         )
    # os.remove(
    #         f'{DATA_PATH}'
    #         f'/progress/progress_{project_id}.json'
    #         )
    fn = f'{DATA_PATH}/input_geometries/raw_input_{project_id}.geojson'
    if os.path.isfile(fn):
        os.remove(fn)
    fn = f'{DATA_PATH}/input_geometries/valid_input_{project_id}.geojson'
    if os.path.isfile(fn):
        os.remove(fn)
    print(
            f'Local files: '
            f'deleted raw_input and valid_input files'
            f'with the project id: {project_id}'
            )


def delete_sample_users(fb_db):
    pass


if __name__ == '__main__':
    fb_db = auth.firebaseDB()
    ref = fb_db.reference('tasks/')
    ref.set({})