from django.urls import path
from . import views

urlpatterns = [
    path('coming-soon/', views.coming_soon, name='coming_soon'),
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('search/api/', views.search_api, name='search_api'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('category/<slug:category_slug>/<slug:subcategory_slug>/', views.subcategory_detail, name='subcategory_detail'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/variants/', views.product_variants_api, name='product_variants_api'),
    
    # Cart URLs
    path('cart/', views.cart_view, name='cart'),
    path('cart/data/', views.cart_data, name='cart_data'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.cart_update_quantity, name='cart_update_quantity'),
    path('cart/remove/<int:item_id>/', views.cart_remove_item, name='cart_remove_item'),
    path('checkout/', views.checkout, name='checkout'),
    
    path('contact/', views.contact, name='contact'),
    path('about-us/', views.about_us, name='about_us'),
    path('accessibility/', views.accessibility_statement, name='accessibility_statement'),
    path('faq/', views.faq, name='faq'),
    path('laundry-instructions/', views.laundry_instructions, name='laundry_instructions'),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    path('shipping/', views.shipping_and_returns, name='shipping_and_returns'),
    
    # Wishlist URLs
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('wishlist/remove/<int:product_id>/', views.wishlist_remove, name='wishlist_remove'),
    
    # Blog URLs
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    
    # Newsletter URLs
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/unsubscribe/<str:token>/', views.newsletter_unsubscribe, name='newsletter_unsubscribe'),
]

