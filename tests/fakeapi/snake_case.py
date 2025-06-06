#!/usr/bin/env python3
def get_path_snake(some_id):
    data = {"SomeId": some_id}
    return data


def get_path_shadow(id_):
    data = {"id": id_}
    return data


def get_query_snake(some_id):
    data = {"someId": some_id}
    return data


def get_query_shadow(list_):
    data = {"list": list_}
    return data


def get_camelcase(truthiness, order_by=None):
    data = {"truthiness": truthiness, "order_by": order_by}
    return data


def post_path_snake(some_id, some_other_id):
    data = {"SomeId": some_id, "SomeOtherId": some_other_id}
    return data


def post_path_shadow(id_, round_):
    data = {"id": id_, "reduce": round_}
    return data


def post_query_snake(some_id, some_other_id):
    data = {"someId": some_id, "someOtherId": some_other_id}
    return data


def post_query_shadow(id_, class_, next_):
    data = {"id": id_, "class": class_, "next": next_}
    return data
