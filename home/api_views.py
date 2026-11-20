from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .views import home_data


@api_view(["GET"])
@permission_classes([AllowAny])
def home(request):
    data = home_data(request.user)
    tip = data["tip"]
    return Response(
        {
            **data,
            "tip": {
                "id": str(tip.pk),
                "title": tip.title,
                "description": tip.description,
            }
            if tip
            else None,
        }
    )
