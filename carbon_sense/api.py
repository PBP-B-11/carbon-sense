from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


def form_data(request):
    data = request.data
    if not isinstance(data, dict) or any(
        isinstance(value, (list, dict)) for value in data.values()
    ):
        raise ValidationError("Kirim objek JSON dengan nilai sederhana.")
    return data


def validate_form(form):
    if not form.is_valid():
        raise ValidationError(form.errors)
    return form.cleaned_data


def paginate(request, queryset, serializer, page_size):
    paginator = PageNumberPagination()
    paginator.page_size = page_size
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(serializer(page, many=True).data)
