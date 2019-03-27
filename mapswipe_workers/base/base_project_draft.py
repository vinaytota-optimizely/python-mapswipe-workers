import os
import logging
import json
import csv
from abc import ABCMeta, abstractmethod

from mapswipe_workers import auth
from mapswipe_workers.definitions import DATA_PATH
from mapswipe_workers.utils import error_handling


class BaseProjectDraft(metaclass=ABCMeta):
    """
    The base class for creating

    Attributes
    ----------
    project_draft_id: str
        The key of a project draft as depicted in firebase
    name : str
        The name of a project
    project_details : str
        The detailed description of the project
    look_for : str
        The objects of interest / objects to look for in this project
    image: str
        The URL of the header image of the project
    verification_count : int
        The number of users required for each task to be finished
    info : dict
        A dictionary containing further attributes\
                set by specific types of projects
    """

    def __init__(self, project_draft):
        """
        The function to initialize a new import

        Parameters
        ----------
        project_draft_id : str
        project_draft: dict
            A dictionary containing all attributes of the project_draft

        Returns
        -------
        bool
           True if successful. False otherwise.
        """

        # check if the submission key is correct
        submission_key = project_draft['submissionKey']
        if not submission_key == auth.get_submission_key():
            raise Exception(f"submission key is not valid: {submission_key}")
        logging.warning(f'{submission_key} - __init__ - start init')

        self.projectId = project_draft['project_draft_id']
        self.projectType = int(project_draft['projectType'])
        self.name = project_draft['name']
        self.projectDetails = project_draft['projectDetails']
        self.image = project_draft['image']
        self.lookFor = project_draft['lookFor']
        self.verificationCount = int(project_draft['verificationCount'])
        self.isFeatured = False
        self.status = 'inactive'
        self.groupAverage = 0
        self.progress = 0
        self.contributors = 0
        self.archived = False

    def create_project(self, fb_db):
        """
        The function to import a new project in firebase and postgres.

        Returns
        -------
        boolean
                True = Suceessful
        """
        try:
            logging.warning(
                f'{self.projectId}'
                f' - import_project - start importing'
                )

            project = vars(self)  
            groups = self.create_groups(self.projectId)
            # extract tasks from groups
            tasks = dict()
            for group_id, group in groups.items():
                tasks[group_id] = group['tasks']
                del group['tasks']

            # upload data to postgres
            self.execute_import_queries(
                    project,
                    groups,
                    tasks,
                    )

            # upload data to firebase
            new_project_ref = fb_db.reference(f'projects/{self.projectId}')
            new_project_ref.set(project)
            logging.warning(
                    f'{self.projectId} - uploaded project in firebase'
                    )

            new_groups_ref = fb_db.reference(f'groups/{self.projectId}/')
            new_groups_ref.set(groups)
            logging.warning('%s - uploaded groups in firebase' % self.projectId)

            new_tasks_ref = fb_db.reference(f'tasks/{self.projectId}/')
            new_tasks_ref.set(tasks)
            logging.warning('%s - uploaded tasks in firebase' % self.projectId)

            logging.warning(
                    '%s - import_project - import finished' % self.projectId
                    )
            logging.warning(
                    f'{self.projectId}'
                    f' - import_project - '
                    f'imported new project with id'
                    )
            return True

        except Exception as e:
            logging.warning(
                    f'{self.projectId}'
                    f' - import_project - '
                    f'could not import project'
                    )
            logging.warning(
                    "%s - import_project - %s" % (self.projectId, e))
            error_handling.log_error(e, logging)
            return False

    def execute_import_queries(self, project, groups, tasks):
        '''
        Defines SQL queries and data for import a project into postgres.
        SQL queries will be executed as transaction.
        (Either every query will be executed or none)
        '''

        query_insert_project = '''
            INSERT INTO projects
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
            '''
        
        data_project = [
                self.projectId,
                self.name,
                self.projectType,
                self.projectDetails,
                self.groupAverage,
                self.contributors,
                self.image,
                self.isFeatured,
                self.lookFor,
                self.progress,
                self.status,
                self.verificationCount,
                self.archived,
        ]

        project_attributes = [
                'projectId',
                'name',
                'projectType',
                'projectDetails',
                'groupAverage',
                'contributors',
                'image',
                'isFeatured',
                'lookFor',
                'progress',
                'status',
                'verificationCount',
                'archived',
                ]

        project_type_specifics = dict()
        for key, value in project.items():
            if key not in project_attributes:
                project_type_specifics[key] = value
        data_project.append(json.dumps(project_type_specifics))

        query_recreate_raw_groups = '''
            DROP TABLE IF EXISTS raw_groups CASCADE;
            CREATE TABLE raw_groups (
              project_id varchar,
              group_id int,
              count int,
              completed_count int,
              verification_count int,
              project_type_specifics json,
              PRIMARY KEY (group_id, project_id),
              FOREIGN KEY (project_id) REFERENCES projects(project_id)
            );
            '''

        query_insert_raw_groups = '''
            INSERT INTO groups
            SELECT *
            FROM raw_groups;
            DROP TABLE IF EXISTS raw_groups CASCADE;
            '''

        query_recreate_raw_tasks = '''
            DROP TABLE IF EXISTS raw_tasks CASCADE;
            CREATE TABLE raw_tasks (
                project_id varchar,
                group_id int,
                task_id varchar,
                project_type_specifics json,
                PRIMARY KEY (task_id, group_id, project_id),
                FOREIGN KEY (project_id) REFERENCES projects(project_id),
                FOREIGN KEY (group_id) REFERENCES groups(group_id)
            );
            '''

        query_insert_raw_tasks = '''
            INSERT INTO tasks
            SELECT *
            FROM raw_tasks;
            DROP TABLE IF EXISTS raw_tasks CASCADE;
            '''

        groups_txt_filename = self.create_groups_txt_file(groups)
        tasks_txt_filename = self.create_tasks_txt_file(groups)

        groups_columns = [
                'project_id',
                'group_id',
                'count',
                'completed_count',
                'verification_count',
                'project_type_specifics'
                ]

        tasks_columns = [
                'projectId',
                'group_id',
                'task_id',
                'project_type_specifics']

        # execution of all SQL-Statements as transaction
        # (either every query gets executed or none)
        try:
            p_con = auth.postgresDB()
            p_con._db_cur = p_con._db_connection.cursor()
            p_con._db_cur.execute(query_insert_project, data_project)
            p_con._db_cur.execute(query_recreate_raw_groups, None)
            p_con._db_cur.execute(query_recreate_raw_tasks, None)
            with open(groups_txt_filename, 'r') as groups_file:
                p_con._db_cur.copy_from(
                        groups_file,
                        'raw_groups',
                        sep='\t',
                        null='\\N',
                        size=8192,
                        columns=groups_columns
                        )
            with open(tasks_txt_filename, 'r') as tasks_file:
                p_con._db_cur.copy_from(
                        tasks_file,
                        'raw_tasks',
                        sep='\t',
                        null='\\N',
                        size=8192,
                        columns=tasks_columns
                        )
            p_con._db_cur.execute(query_insert_raw_groups, None)
            p_con._db_cur.execute(query_insert_raw_tasks, None)
            p_con._db_connection.commit()
            p_con._db_cur.close()
        except Exception as e:
            del p_con
            raise

        os.remove(groups_txt_filename)
        os.remove(tasks_txt_filename)

    def create_groups_txt_file(self, groups):
        """
        Creates a text file containing groups information
        for a specific project.
        The text file is temporary and used only by BaseImport module.

        Parameters
        ----------
        projectId : int
            The id of the project
        groups : dict
            The dictionary with the group information

        Returns
        -------
        string
            Filename
        """

        if not os.path.isdir('{}/tmp'.format(DATA_PATH)):
            os.mkdir('{}/tmp'.format(DATA_PATH))

        # create txt file with header for later
        # import with copy function into postgres
        groups_txt_filename = f'{DATA_PATH}/tmp/raw_groups_{self.projectId}.txt'
        groups_txt_file = open(groups_txt_filename, 'w', newline='')
        fieldnames = (
                'project_id',
                'group_id',
                'count',
                'completed_count',
                'verification_count',
                'project_type_specifics'
                )
        w = csv.DictWriter(
                groups_txt_file,
                fieldnames=fieldnames,
                delimiter='\t',
                quotechar="'",
                )

        for group in groups:
            try:
                output_dict = {
                    "project_id": self.projectId,
                    "group_id": int(groups[group]['id']),
                    "count": int(groups[group]['count']),
                    "completed_count": int(groups[group]['completedCount']),
                    "verification_count": int(
                        groups[group]['verificationCount']
                        ),
                    "project_type_specifics": {}
                }

                for key in groups[group].keys():
                    if key not in [
                            'project_id',
                            'group_id',
                            'count',
                            'completed_count',
                            'verification_count',
                            'tasks'
                            ]:
                        output_dict['project_type_specifics'][key] = groups[group][key]
                output_dict['project_type_specifics'] = json.dumps(output_dict['project_type_specifics'])

                w.writerow(output_dict)

            except Exception as e:
                logging.warning(
                        f'{self.project_id}'
                        f' - set_groups_postgres - '
                        f'groups missed critical information: {e}'
                        )
                error_handling.log_error(e, logging)

        groups_txt_file.close()

        return groups_txt_filename

    def create_tasks_txt_file(self, tasks):
        """
        Creates a text file containing tasks information
        for a specific project.
        It interates over groups and extracts tasks.
        The text file is temporary and used only by BaseImport module.

        Parameters
        ----------
        projectId : int
            The id of the project
        tasks : dictionary
            Dictionary containing tasks of a project

        Returns
        -------
        string
            Filename
        """

        if not os.path.isdir('{}/tmp'.format(DATA_PATH)):
            os.mkdir('{}/tmp'.format(DATA_PATH))

        # save tasks in txt file
        tasks_txt_filename = f'{DATA_PATH}/tmp/raw_tasks_{self.projectId}.txt'
        tasks_txt_file = open(tasks_txt_filename, 'w', newline='')

        fieldnames = (
                'project_id',
                'group_id', 
                'task_id',
                'project_type_specifics'
                )
        w = csv.DictWriter(
                tasks_txt_file,
                fieldnames=fieldnames,
                delimiter='\t',
                quotechar="'",
                )

        for task in tasks:
            try:
                output_dict = {
                        "project_id": self.project_id,
                        "group_id": task['group_id'],
                        "task_id": str(task['task_id']),
                        "project_type_specifics": dict()
                        }
                for key in task.keys():
                    if key not in [
                            'project_id',
                            'group_id'
                            'task_id',
                            ]:
                        output_dict['project_type_specifics'][key] = [task][key]
                output_dict['project_type_specifics'] = json.dumps(output_dict['project_type_specifics'])

                w.writerow(output_dict)
            except Exception as e:
                logging.warning(
                        f'{self.projectId}'
                        f' - set_tasks_postgres - '
                        f'tasks missed critical information: {e}'
                        )
        tasks_txt_file.close()
        return tasks_txt_filename

    @abstractmethod
    def validate_geometries():
        pass

    @abstractmethod
    def create_groups():
        pass
