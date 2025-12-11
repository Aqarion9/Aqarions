from rest_framework import viewsets
from .models import Node, Link
from .serializers import NodeSerializer, LinkSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
import random

class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer

    @action(detail=False, methods=['post'])
    def generate_graph(self, request):
        Node.objects.all().delete()
        Link.objects.all().delete()
        nodes = []
        for i in range(5):
            nodes.append(Node.objects.create(name=f'Node{i}', x=random.random()*10, y=random.random()*10, z=random.random()*10))
        for i in range(5):
            Link.objects.create(source=random.choice(nodes), target=random.choice(nodes))
        return Response({'nodes': len(nodes), 'links': Link.objects.count()})

class LinkViewSet(viewsets.ModelViewSet):
    queryset = Link.objects.all()
    serializer_class = LinkSerializer
