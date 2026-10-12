from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """`?page=N&page_size=M` pagination with a hard upper bound."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
