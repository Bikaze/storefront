from django.urls import path, include
from rest_framework_nested import routers
from .views import CartItemViewSet, CartViewSet, CustomerViewSet, OrderItemViewSet, OrderViewSet, ProductViewSet, CollectionViewSet, ReviewViewSet

router = routers.DefaultRouter()
router.register('products', ProductViewSet, basename='products')
router.register('collections', CollectionViewSet)
router.register('carts', CartViewSet)
router.register('customers', CustomerViewSet)
router.register('orders', OrderViewSet, basename='orders')

products_router = routers.NestedDefaultRouter(router, 'products', lookup='product')
products_router.register('reviews', ReviewViewSet, basename='product-reviews')
cartItem_router = routers.NestedDefaultRouter(router, 'carts', lookup='cart')
cartItem_router.register('items', CartItemViewSet, basename='cart-items')
orderItem_router = routers.NestedDefaultRouter(router, 'orders', lookup='order')
orderItem_router.register('items', OrderItemViewSet, basename='order-items')


urlpatterns = [
    path('', include(router.urls)),
    path('', include(products_router.urls)),
    path('', include(cartItem_router.urls)),
    path('', include(orderItem_router.urls)),
]

# urlpatterns = [
    # path('', include(router.urls)), # use this if you have some more urls to map other than those in the router.urls
    # path('
    # path('', include(products/', views.ProductList.as_view()),
#     path('
# path('', include(products/<int:pk>/', views.ProductDetail.as_view()),
    # path('
    # path('', include(collections/', views.CollectionList.as_view()),
    # path('collections/<int:pk>/', views.CollectionDetail.as_view(), name='collection-detail')
# ]