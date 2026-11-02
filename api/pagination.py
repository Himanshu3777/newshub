from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    """Default 20 per page; clients may ask for more but never beyond 100,
    so a single request cannot pull the whole catalogue."""
    page_size=20
    page_size_query_param="page_size"
    max_page_size=100
