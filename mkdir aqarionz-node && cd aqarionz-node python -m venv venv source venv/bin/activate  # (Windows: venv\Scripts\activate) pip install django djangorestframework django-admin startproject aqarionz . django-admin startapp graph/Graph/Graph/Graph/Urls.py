from rest_framework.routers import DefaultRouter
from .views import NodeViewSet, LinkViewSet
from django.urls import path, include

router = DefaultRouter()
router.register('nodes', NodeViewSet)
router.register('links', LinkViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
