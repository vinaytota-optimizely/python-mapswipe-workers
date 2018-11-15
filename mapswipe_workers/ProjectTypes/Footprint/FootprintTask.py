from mapswipe_workers.basic.BaseTask import *


class FootprintTask(BaseTask):
    def __init__(self, group, project, feature_id, feature_geometry):
        # super() executes fine now
        task_id = '{}_{}_{}'.format(
            project.id, group.id, feature_id
        )

        super(FootprintTask, self).__init__(group, task_id)
        self.type = 2
        self.info = {
            "feature_id": feature_id,
            "geojson": feature_geometry
        }