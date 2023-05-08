from abc import ABCMeta, abstractmethod

from utils import NULL_REPR


class SDC:
    __metaclass__ = ABCMeta

    def __init__(self, x, y, attr, weight_function="1/(distance+1)"):
        """
        alternative weight functions:
            - 1 / (distance + 1)
            - exp(-distance / 1000)
        """
        self.x = x
        self.y = y
        self.attr = attr
        self.weight_function = weight_function
        self.geom_table_name = f"geom_{self.x}{self.y}"
        self.distance_matrix_table_name = None
        self.set_error = None  # set of tid
        self.dict_domain = None  # {tid: domain}
        self.labeling_count = None  # {tid: {dv: count}}
        self.weight_sum = None  # {tid: {dv: weight_sum}}

    def get_error_sql(self):
        sql = f'''
        SELECT DISTINCT tid_1 FROM {self.distance_matrix_table_name} 
        WHERE val_1 <> val_2 AND val_1 <> '{NULL_REPR}' AND val_2 <> '{NULL_REPR}'
        UNION 
        SELECT DISTINCT tid_2 FROM {self.distance_matrix_table_name} 
        WHERE val_1 <> val_2 AND val_1 <> '{NULL_REPR}' AND val_2 <> '{NULL_REPR}'
        '''
        return sql

    def get_domain_sql(self):
        sql = f"SELECT tid_1, ARRAY_AGG(DISTINCT val_2) as domain FROM {self.distance_matrix_table_name} WHERE val_2 <> '{NULL_REPR}' GROUP BY tid_1"
        return sql

    def get_label_feature_sql(self):
        sql = f"SELECT tid_1, val_2, COUNT(1) as count, SUM(weight) as weight FROM {self.distance_matrix_table_name} WHERE val_2 <> '{NULL_REPR}' GROUP BY tid_1, val_2"
        return sql

    @abstractmethod
    def setup_specific_literal(self):
        raise NotImplementedError

    @abstractmethod
    def gen_create_dm_sql(self):
        raise NotImplementedError


class KnnSDC(SDC):
    def __init__(self, x, y, attr, k, weight_function="1/(distance+1)"):
        super().__init__(x, y, attr, weight_function)
        self.knn = k
        self.use_knn = True
        self.use_distance = False
        self.setup_specific_literal()

    def __repr__(self):
        return f"KnnSDC(x: {self.x}, y: {self.y}, attr: {self.attr}, k: {self.knn})"

    def setup_specific_literal(self):
        self.weight_function = self.weight_function.replace("distance", "t2.dist")
        self.distance_matrix_table_name = f"distance_matrix_{self.attr}_k{self.knn}"

    def gen_create_dm_sql(self):
        sql_create_dm = f'''
                SELECT
                    t1._tid_ AS tid_1,
                    t1.{self.attr} AS val_1,
                    t2._tid_ AS tid_2,
                    t2.{self.attr} AS val_2,
                    t2.dist AS distance,
                    {self.weight_function} as weight
                FROM
                    {self.geom_table_name} AS t1
                    CROSS JOIN LATERAL (
                        SELECT
                            _tid_,
                            {self.attr},
                            t1._geom_ <-> t2._geom_ AS dist
                        FROM
                            {self.geom_table_name} t2
                        WHERE
                            t1._tid_ <> t2._tid_
                            AND t2.{self.attr} <> '{NULL_REPR}'
                        ORDER BY dist
                        LIMIT {self.knn}) AS t2
                '''
        return sql_create_dm


class DistanceSDC(SDC):
    def __init__(self, x, y, attr, d, weight_function="1/(distance+1)"):
        super().__init__(x, y, attr, weight_function)
        self.distance = d
        self.use_knn = False
        self.use_distance = True
        self.setup_specific_literal()

    def __repr__(self):
        return f"DistanceSDC(x: {self.x}, y: {self.y}, attr: {self.attr}, distance: {self.distance})"

    def setup_specific_literal(self):
        self.weight_function = self.weight_function.replace("distance", "ST_Distance(t1._geom_, t2._geom_)")
        self.distance_matrix_table_name = f"distance_matrix_{self.attr}_d{self.distance}"

    def gen_create_dm_sql(self):
        sql_create_dm = f'''
                SELECT
                    t1._tid_ AS tid_1,
                    t1.{self.attr} AS val_1,
                    t2._tid_ AS tid_2,
                    t2.{self.attr} AS val_2,
                    ST_Distance(t1._geom_, t2._geom_) AS distance,
                    {self.weight_function} as weight
                FROM 
                    {self.geom_table_name} t1, 
                    {self.geom_table_name} t2
                WHERE ST_DWithin(t1._geom_, t2._geom_, {self.distance})
                  AND t1._tid_ <> t2._tid_
                '''
        return sql_create_dm