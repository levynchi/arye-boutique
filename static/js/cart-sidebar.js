// Cart Sidebar Management

document.addEventListener('DOMContentLoaded', function() {
    const cartTrigger = document.getElementById('cart-trigger');
    const cartSidebar = document.getElementById('cart-sidebar');
    const cartOverlay = document.getElementById('cart-sidebar-overlay');
    const cartClose = document.getElementById('cart-sidebar-close');
    const continueShopping = document.getElementById('sidebar-continue-shopping');
    const focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex=\"-1\"])';
    let lastFocusedElement = null;
    
    // Open cart sidebar
    function openCartSidebar() {
        lastFocusedElement = document.activeElement;
        cartSidebar.classList.add('active');
        cartOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        cartSidebar.setAttribute('aria-hidden', 'false');
        cartOverlay.setAttribute('aria-hidden', 'false');
        cartTrigger.setAttribute('aria-expanded', 'true');
        cartSidebar.addEventListener('keydown', trapFocus);
        loadCartData();
        setTimeout(focusFirstElement, 0);
    }
    
    // Close cart sidebar
    function closeCartSidebar() {
        cartSidebar.classList.remove('active');
        cartOverlay.classList.remove('active');
        document.body.style.overflow = '';
        cartSidebar.setAttribute('aria-hidden', 'true');
        cartOverlay.setAttribute('aria-hidden', 'true');
        cartTrigger.setAttribute('aria-expanded', 'false');
        cartSidebar.removeEventListener('keydown', trapFocus);
        if (lastFocusedElement) {
            lastFocusedElement.focus();
            lastFocusedElement = null;
        } else {
            cartTrigger.focus();
        }
    }

    function getFocusableElements() {
        return cartSidebar.querySelectorAll(focusableSelectors);
    }

    function focusFirstElement() {
        const focusableElements = getFocusableElements();
        if (focusableElements.length > 0) {
            focusableElements[0].focus();
        } else {
            cartSidebar.focus();
        }
    }

    function trapFocus(event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            closeCartSidebar();
            return;
        }

        if (event.key !== 'Tab') {
            return;
        }

        const focusableElements = getFocusableElements();
        if (!focusableElements.length) {
            event.preventDefault();
            return;
        }

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) {
            if (document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            }
        } else {
            if (document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }
    }
    
    // Load cart data from API
    function loadCartData() {
        fetch('/cart/data/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renderCartItems(data);
                    updateCartSummary(data);
                }
            })
            .catch(error => {
                console.error('Error loading cart:', error);
            });
    }
    
    // Render cart items
    function renderCartItems(data) {
        const cartItemsContainer = document.getElementById('cart-sidebar-items');
        const cartEmpty = document.getElementById('cart-sidebar-empty');
        const cartFooter = document.querySelector('.cart-sidebar-footer');
        const sidebarCount = document.getElementById('sidebar-cart-count');
        
        // Update count
        sidebarCount.textContent = data.total_items;
        
        if (data.items.length === 0) {
            // Show empty state
            cartItemsContainer.style.display = 'none';
            cartFooter.style.display = 'none';
            cartEmpty.style.display = 'block';
        } else {
            // Show cart items
            cartItemsContainer.style.display = 'flex';
            cartFooter.style.display = 'block';
            cartEmpty.style.display = 'none';
            
            cartItemsContainer.innerHTML = data.items.map(item => `
                <div class="cart-sidebar-item" data-item-id="${item.id}" role="listitem">
                    <div class="cart-sidebar-item-image">
                        <img src="${item.product_image}" alt="${item.product_name}">
                    </div>
                    
                    <div class="cart-sidebar-item-details">
                        <h3 class="cart-sidebar-item-name">${item.product_name}</h3>
                        ${item.product_subtitle ? `<p class="cart-sidebar-item-subtitle">${item.product_subtitle}</p>` : ''}
                        ${item.variant_display ? `<p class="cart-sidebar-item-variant">${item.variant_display}</p>` : ''}
                        ${item.product_size && !item.variant_display ? `<p class="cart-sidebar-item-size">${item.product_size}</p>` : ''}
                        <p class="cart-sidebar-item-price">${item.product_price.toFixed(2)} ₪</p>
                    </div>
                    
                    <div class="cart-sidebar-item-actions">
                        <button class="sidebar-remove-btn" data-item-id="${item.id}" title="הסר" aria-label="הסר את ${item.product_name} מהעגלה">×</button>
                        
                        <div class="sidebar-quantity-controls">
                            <button class="sidebar-quantity-btn sidebar-quantity-decrease" data-item-id="${item.id}" aria-label="הקטן כמות עבור ${item.product_name}">-</button>
                            <input type="number" class="sidebar-quantity-input" value="${item.quantity}" min="1" max="${item.max_quantity}" data-item-id="${item.id}" readonly aria-label="כמות עבור ${item.product_name}">
                            <button class="sidebar-quantity-btn sidebar-quantity-increase" data-item-id="${item.id}" aria-label="הגדל כמות עבור ${item.product_name}">+</button>
                        </div>
                    </div>
                </div>
            `).join('');
            
            // Attach event listeners to new elements
            attachItemEventListeners();
        }
    }
    
    // Update cart summary
    function updateCartSummary(data) {
        const shippingElement = document.getElementById('sidebar-shipping');
        const totalElement = document.getElementById('sidebar-total');
        const shippingNotice = document.getElementById('sidebar-shipping-notice');
        const remainingElement = document.getElementById('sidebar-remaining');
        
        // הצג רק את סכום הפריטים (subtotal) בתור סה״כ
        totalElement.textContent = `${data.subtotal.toFixed(2)} ₪`;
        
        if (data.subtotal >= data.free_shipping_threshold) {
            shippingElement.textContent = 'חינם';
            shippingNotice.style.display = 'none';
        } else if (data.subtotal > 0) {
            shippingElement.textContent = `${data.shipping_fee.toFixed(2)} ₪`;
            shippingNotice.style.display = 'block';
            remainingElement.textContent = data.remaining_for_free_shipping.toFixed(2);
        } else {
            shippingElement.textContent = 'חינם';
            shippingNotice.style.display = 'none';
        }
        
        // Update header cart count
        const headerCartCount = document.getElementById('cart-count');
        if (headerCartCount) {
            headerCartCount.textContent = data.total_items;
        }
    }
    
    // Attach event listeners to cart items
    function attachItemEventListeners() {
        // Remove buttons
        document.querySelectorAll('.sidebar-remove-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                removeCartItem(itemId);
            });
        });
        
        // Increase quantity
        document.querySelectorAll('.sidebar-quantity-increase').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const input = document.querySelector(`.sidebar-quantity-input[data-item-id="${itemId}"]`);
                const currentValue = parseInt(input.value);
                const maxValue = parseInt(input.max);
                
                if (currentValue < maxValue) {
                    updateCartItemQuantity(itemId, currentValue + 1);
                } else {
                    showMessage('הגעת למלאי המקסימלי של מוצר זה', 'warning');
                }
            });
        });
        
        // Decrease quantity
        document.querySelectorAll('.sidebar-quantity-decrease').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const input = document.querySelector(`.sidebar-quantity-input[data-item-id="${itemId}"]`);
                const currentValue = parseInt(input.value);
                
                if (currentValue > 1) {
                    updateCartItemQuantity(itemId, currentValue - 1);
                } else {
                    showMessage('הכמות המינימלית היא 1', 'warning');
                }
            });
        });
    }
    
    // Update cart item quantity
    function updateCartItemQuantity(itemId, newQuantity) {
        const formData = new FormData();
        formData.append('quantity', newQuantity);
        
        fetch(`/cart/update/${itemId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the input value
                const input = document.querySelector(`.sidebar-quantity-input[data-item-id="${itemId}"]`);
                if (input) {
                    input.value = newQuantity;
                }
                
                // Reload cart data to update totals
                loadCartData();
            } else {
                showMessage(data.error || 'אירעה שגיאה בעדכון הכמות', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('אירעה שגיאה בעדכון הכמות', 'error');
        });
    }
    
    // Remove cart item
    function removeCartItem(itemId) {
        if (!confirm('האם אתה בטוח שברצונך להסיר מוצר זה מהעגלה?')) {
            return;
        }
        
        fetch(`/cart/remove/${itemId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(data.message, 'success');
                // Reload cart data
                loadCartData();
            } else {
                showMessage(data.error || 'אירעה שגיאה בהסרת המוצר', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('אירעה שגיאה בהסרת המוצר', 'error');
        });
    }
    
    // Show message to user
    function showMessage(message, type = 'info') {
        const messagesContainer = document.querySelector('.messages-container') || createMessagesContainer();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.textContent = message;
        
        const closeButton = document.createElement('button');
        closeButton.className = 'message-close';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', function() {
            messageDiv.style.transition = 'opacity 0.3s ease';
            messageDiv.style.opacity = '0';
            setTimeout(() => messageDiv.remove(), 300);
        });
        
        messageDiv.appendChild(closeButton);
        messagesContainer.appendChild(messageDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentElement) {
                messageDiv.style.transition = 'opacity 0.3s ease';
                messageDiv.style.opacity = '0';
                setTimeout(() => messageDiv.remove(), 300);
            }
        }, 5000);
    }
    
    // Create messages container if it doesn't exist
    function createMessagesContainer() {
        const container = document.createElement('div');
        container.className = 'messages-container';
        const mainContent = document.querySelector('.main-content');
        mainContent.insertBefore(container, mainContent.firstChild);
        return container;
    }
    
    // Get CSRF token from cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Event listeners
    if (cartTrigger) {
        cartTrigger.addEventListener('click', openCartSidebar);
    }
    
    if (cartClose) {
        cartClose.addEventListener('click', closeCartSidebar);
    }
    
    if (cartOverlay) {
        cartOverlay.addEventListener('click', closeCartSidebar);
    }
    
    if (continueShopping) {
        continueShopping.addEventListener('click', closeCartSidebar);
    }
    
    // Also attach to empty state continue button
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('sidebar-continue-btn')) {
            closeCartSidebar();
        }
    });
    
    // Make function globally accessible for add to cart
    window.openCartSidebar = openCartSidebar;
});


