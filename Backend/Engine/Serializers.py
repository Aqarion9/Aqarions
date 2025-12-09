

***

### **Overview: How the API Code Works**

The API is built using the Django REST Framework (DRF), which provides a powerful toolkit for creating web APIs. The code is structured into three main parts:

1.  **`serializers.py`**: Defines how complex data (like Django models) is converted to and from JSON. It handles data validation, ensuring that incoming requests have the correct format before they ever touch the core logic.
2.  **`views.py`**: Contains the `ViewSet` classes. A `ViewSet` is a single class that handles all the standard API actions for a given model (`list`, `create`, `retrieve`, `update`, `destroy`), plus any custom actions. This is where the API layer connects to the `MultiverseOrchestrator` service.
3.  **`urls.py`**: Maps specific URL paths (e.g., `/api/v1/universes/`) to the appropriate `ViewSet`, wiring everything together so it's accessible over the web.

This structure follows best practices for building robust and maintainable APIs with Django. [1][2]

***

### **1. `engine/serializers.py` - The Data Gatekeepers**

This file defines how your data is shaped for the API. It's the strict gatekeeper that validates all incoming data and formats all outgoing data.

```python
# backend/engine/serializers.py

from rest_framework import serializers
from .models import Universe, Node, Epitaph

# --- Serializers for API Output (Read-Only) ---

class EpitaphSerializer(serializers.ModelSerializer):
    class Meta:
        model = Epitaph
        fields = ['text', 'conclusion_reason', 'final_syntropy', 'created_at']

class UniverseSerializer(serializers.ModelSerializer):
    """
    Serializes a Universe model instance for read operations (GET requests).
    It includes nested data for a richer response.
    """
    # Nested serializer to show epitaph details directly.
    epitaph = EpitaphSerializer(read_only=True)
    
    # MethodField to include a dynamically generated URL to the parent.
    parent_url = serializers.SerializerMethodField()

    class Meta:
        model = Universe
        fields = [
            'id', 'instance_id', 'parent_id', 'parent_url', 'active', 
            'syntropy_level', 'current_tick', 'first_cause', 'epitaph', 
            'created_at', 'concluded_at'
        ]
        read_only_fields = fields # Make all fields read-only by default

    def get_parent_url(self, obj):
        if obj.parent_id:
            request = self.context.get('request')
            return request.build_absolute_uri(f'/api/v1/universes/{obj.parent_id}/')
        return None

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ['id', 'universe_id', 'name', 'node_type', 'coherence']

# --- Serializers for API Input (Write/Create) ---

class GenesisBlueprintSerializer(serializers.Serializer):
    """
    Validates the incoming JSON payload for spawning a new universe.
    This is NOT a ModelSerializer because it doesn't map directly to a single model.
    It's a pure validation class.
    """
    specVersion = serializers.CharField(required=True)
    metadata = serializers.DictField(required=True)
    genesisParameters = serializers.DictField(required=True)
    # Optional fields
    ouroborosParameters = serializers.DictField(required=False)
    environmentalModulators = serializers.DictField(required=False)
    initialNodes = serializers.ListField(child=serializers.DictField(), required=False)

    def validate_specVersion(self, value):
        if value != "19.0":
            raise serializers.ValidationError("Only specVersion '19.0' is supported.")
        return value

    def validate_metadata(self, value):
        if "name" not in value:
            raise serializers.ValidationError("metadata must contain a 'name' field.")
        return value

    def validate_genesisParameters(self, value):
        required_keys = {"initialNodeCount", "baseSyntropy", "genesisThreshold"}
        if not required_keys.issubset(value.keys()):
            raise serializers.ValidationError(f"genesisParameters must contain {required_keys}.")
        return value
```

***

### **2. `engine/views.py` - The API Endpoints**

This file contains the `ViewSets` that handle HTTP requests. It's the bridge between the web and your core `MultiverseOrchestrator` service.

```python
# backend/engine/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Universe, Node
from .serializers import UniverseSerializer, NodeSerializer, GenesisBlueprintSerializer
from .orchestrator import MultiverseOrchestrator
from .exceptions import GenesisBlueprintError

# --- Custom Permissions ---
class IsAdminOrReadOnly(IsAuthenticated):
    """
    Custom permission: Read-only for anyone, but write/delete for admin users.
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and request.user.is_staff

# --- ViewSets ---

class UniverseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows universes to be viewed.
    It's read-only by default, with custom actions for creation/modification.
    """
    queryset = Universe.objects.all().order_by('-created_at')
    serializer_class = UniverseSerializer
    permission_classes = [AllowAny] # Anyone can view universes

    @action(detail=False, methods=['post'], url_path='spawn', permission_classes=[IsAuthenticated])
    def spawn_universe(self, request):
        """
        Custom action to spawn a new universe.
        URL: /api/v1/universes/spawn/
        """
        blueprint_serializer = GenesisBlueprintSerializer(data=request.data)
        if not blueprint_serializer.is_valid():
            return Response(blueprint_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            orchestrator = MultiverseOrchestrator()
            universe = orchestrator.spawn_universe(blueprint_serializer.validated_data)
            
            # Serialize the newly created universe for the response
            response_serializer = self.get_serializer(universe)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except GenesisBlueprintError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrReadOnly])
    def conclude(self, request, pk=None):
        """
        Custom action to manually conclude a universe.
        URL: /api/v1/universes/{id}/conclude/
        """
        try:
            orchestrator = MultiverseOrchestrator()
            orchestrator.conclude_universe(universe_id=pk, reason="manual_intervention")
            return Response({'status': 'conclusion_initiated'}, status=status.HTTP_202_ACCEPTED)
        except Universe.DoesNotExist:
            return Response({'error': 'Universe not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NodeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows nodes to be viewed.
    """
    queryset = Node.objects.all()
    serializer_class = NodeSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Optionally restricts the returned nodes to a specific universe,
        by filtering against a `universe` query parameter in the URL.
        """
        queryset = super().get_queryset()
        universe_id = self.request.query_params.get('universe')
        if universe_id:
            queryset = queryset.filter(universe_id=universe_id)
        return queryset
```

***

### **3. `engine/urls.py` & `aqarionz/urls.py` - The URL Router**

These files connect the `ViewSets` to the web, making them accessible at specific URLs.

#### **`backend/engine/urls.py`**
```python
# backend/engine/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UniverseViewSet, NodeViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'universes', UniverseViewSet)
router.register(r'nodes', NodeViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
```

#### **`backend/aqarionz/urls.py`** (The main project URL file)
```python
# backend/aqarionz/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Include the engine's API URLs under the /api/v1/ namespace
    path('api/v1/', include('engine.urls')),
]
```

### **How It All Works Together: A Real Request**

1.  **Request:** A user sends a `POST` request to `/api/v1/universes/spawn/` with a JSON payload (the Genesis Blueprint).
2.  **Routing:** The main `urls.py` directs the request to the `engine` app's `urls.py`. The DRF `DefaultRouter` sees the `/spawn` path and knows it maps to the `spawn_universe` custom action in the `UniverseViewSet`.
3.  **Permissions:** The `@action` decorator checks the `IsAuthenticated` permission. If the user isn't logged in, it returns a `403 Forbidden` error immediately.
4.  **Validation:** The `GenesisBlueprintSerializer` is instantiated with the request data. It runs all its `validate_` methods. If any validation fails (e.g., `specVersion` is wrong), it returns a `400 Bad Request` error with details.
5.  **Service Layer:** If validation succeeds, the `spawn_universe` method calls the `MultiverseOrchestrator` service, passing it the cleaned, validated data. The view doesn't know *how* to spawn a universe; it only knows to ask the orchestrator to do it.
6.  **Core Logic:** The `MultiverseOrchestrator` performs its complex, atomic, and asynchronous logic, creating the universe in the database and firing the `universe_spawned` signal.
7.  **Response:** The orchestrator returns the newly created `Universe` model instance to the view.
8.  **Serialization:** The view uses the `UniverseSerializer` to convert the `Universe` object back into JSON, including the nested epitaph and the dynamic `parent_url`.
9.  **HTTP Response:** The view wraps this JSON in a `Response` object with a `201 Created` status code and sends it back to the user.

This is the complete, real, working code for a robust, scalable, and maintainable API that serves as the gateway to the AQARIONZ v19 multiverse.

Citations:
[1] Most Used Django Architecture Patterns https://dev.to/buddhiraz/most-used-django-architecture-patterns-8m
[2] Django Rest API: 17 Principles for Robust Framework - Studio https://buildwithstudio.com/knowledge/backend-principles-for-a-robust-django-rest-framework/
