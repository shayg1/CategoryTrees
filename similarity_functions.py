class Jaccard(object):
    def __init__(self, delta):
        self.name = 'Jaccard'
        self.eps = 0.0001
        self.delta = delta

    def __repr__(self):
        return self.name + ' ' + str(self.delta)

    def compute_relation(self, q1, q2):
        inter = len(q1 & q2)
        len_q1, len_q2 = len(q1), len(q2)
        together = self.can_together(len_q1, len_q2, inter)
        separately = self.can_separately(len_q1, len_q2, inter)
        conflict = (not together) and (not separately)
        if conflict:
            return -1
        must = (together and (not separately)) or (together and separately and (together > (separately + self.eps)))
        if must:
            return 1
        else:
            return 0

    def can_together(self, q1, q2, inter):
        must_remain = max(inter, self.delta * q2)  # must remain in q2
        lb_extra = must_remain - inter
        ub_extra = q1 * (1 - self.delta) / self.delta
        if lb_extra > (ub_extra - self.eps):
            return 0
        extra = min(q2 - inter, ub_extra)
        score = (q1 / (q1 + extra)) + ((inter + extra) / q2)
        return score

    def can_separately(self, q1, q2, inter):
        ub_x = min(inter, (1 - self.delta) * q2)  # this is how much q1 can take from inter
        lb_x = inter - (q1 * (1 - self.delta))
        if lb_x > (ub_x - self.eps):
            return 0
        score = ((q1 - inter + lb_x) / q1) + ((q2 - lb_x) / q2)
        return score

    def is_covering(self, q, cat):
        inter = len(q & cat)
        union = len(q) + len(cat) - inter
        score = (inter / union)
        return score > (self.delta - self.eps)

    def num_missing(self,q, cat):
        inter_len = len(set.intersection(cat, q))
        union_len = len(cat) + len(q) - inter_len
        return (union_len * self.delta) - inter_len


class F1(object):
    def __init__(self, delta):
        self.name = 'F1'
        self.eps = 0.0001
        self.delta = delta

    def __repr__(self):
        return self.name + ' ' + str(self.delta)

    def compute_relation(self, q1, q2):
        inter = len(set.intersection(q1.elms,q2.elms))
        len_q1, len_q2 = len(q1.elms), len(q2.elms)
        together = self.can_together(len_q1, len_q2, inter)
        separately = self.can_separately(len_q1, len_q2, inter)
        conflict = (not together) and (not separately)
        if conflict:
            return -1
        must = (together and (not separately)) or (together and separately and (together > (separately + self.eps)))
        if must:
            return 1
        else:
            return 0

    def can_together(self, q1, q2, inter):
        must_remain = max(inter, q2 * (self.delta / 2) / (1 - self.delta / 2))  # must remain in q2
        lb_extra = must_remain - inter
        ub_extra = q1 * (1 - self.delta) / (self.delta / 2)
        if lb_extra > (ub_extra - self.eps):
            return 0
        extra = min(q2 - inter, ub_extra)
        if extra < 0 or q1 <= 0 or inter > q1 or inter > q2:
            print('ERROR', q1, q2, inter, ub_extra, lb_extra, extra)
        p1 = q1 / (q1 + extra)
        r2 = (inter + extra) / q2
        score = 2 * ((p1) / (1 + p1) + (r2) / (1 + r2))
        return score

    def can_separately(self, q1, q2, inter):
        ub_x = min(inter, (1 - self.delta) / (1 - (self.delta / 2)) * q2)  # this is how much q1 can take from inter
        lb_x = inter - (q1 * (1 - self.delta) / (1 - (self.delta / 2)))
        if lb_x > (ub_x - self.eps):
            return 0
        r1 = (q1 - inter + lb_x) / q1
        r2 = (q2 - lb_x) / q2
        score = 2 * ((r1) / (1 + r1) + (r2) / (1 + r2))
        return score

    def is_covering(self, q, cat):
        inter = len(q & cat)
        if (not len(cat)) or (not inter):
            return False
        precision = inter / len(cat)
        recall = inter / len(q)
        score = 2 * (precision * recall) / (precision + recall)
        return score > (self.delta - self.eps)

    def num_missing(self,q, cat):
        inter_len = len(set.intersection(cat, q))
        half_delta = self.delta / 2
        return (half_delta * (len(q) + len(cat)) - inter_len) / (1 - half_delta)


class PerfectRecall(object):
    def __init__(self, delta):
        self.name = 'Perfect-Recall'
        self.eps = 0.001
        self.delta = delta

    def __repr__(self):
        return self.name + ' ' + str(self.delta)

    def compute_relation(self, q1, q2):
        len_q1, len_q2 = len(q1), len(q2)
        together = self.can_together(len_q1, len_q2, len(q1 | q2))
        if not together:
            return -1
        return 1


    def can_together(self, q1, q2, union):
        precision = q1 / union
        return precision > self.delta + self.eps

    def is_covering(self, q, cat):
        if not q.issubset(cat):
            return False
        inter = len(q & cat)
        precision = inter / len(cat)
        return precision > (self.delta - self.eps)


class Exact(object):
    def __init__(self, delta = 1):
        self.name = 'Exact'
        self.eps = 0.001

    def __repr__(self):
        return self.name

    def compute_relation(self, q1, q2):
        if q2.elms.issubset(q1.elms):
            return 1
        return -1

    def is_covering(self, q, cat):
        return q.equals(cat)