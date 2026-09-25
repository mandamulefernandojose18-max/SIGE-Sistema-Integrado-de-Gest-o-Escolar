from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'limit'
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'total': self.page.paginator.count,
            'count': self.page.paginator.count,
            'page': self.page.number,
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'data': data,
            'results': data
        })
