// Cart Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Quantity Update Handlers
    const increaseButtons = document.querySelectorAll('.quantity-increase');
    const decreaseButtons = document.querySelectorAll('.quantity-decrease');
    const removeButtons = document.querySelectorAll('.remove-item-btn');
    
    // Handle quantity increase
    increaseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            const input = document.querySelector(`.quantity-input[data-item-id="${itemId}"]`);
            const currentValue = parseInt(input.value);
            const maxValue = parseInt(input.max);
            
            if (currentValue < maxValue) {
                updateQuantity(itemId, currentValue + 1);
            } else {
                showMessage('הגעת למלאי המקסימלי של מוצר זה', 'warning');
            }
        });
    });
    
    // Handle quantity decrease
    decreaseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            const input = document.querySelector(`.quantity-input[data-item-id="${itemId}"]`);
            const currentValue = parseInt(input.value);
            
            if (currentValue > 1) {
                updateQuantity(itemId, currentValue - 1);
            } else {
                showMessage('הכמות המינימלית היא 1', 'warning');
            }
        });
    });
    
    // Handle remove item
    removeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            if (confirm('האם אתה בטוח שברצונך להסיר מוצר זה מהעגלה?')) {
                removeItem(itemId);
            }
        });
    });
    
    // Update quantity via AJAX
    function updateQuantity(itemId, newQuantity) {
        const formData = new FormData();
        formData.append('quantity', newQuantity);
        
        fetch(`/cart/update/${itemId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update quantity input
                const input = document.querySelector(`.quantity-input[data-item-id="${itemId}"]`);
                input.value = newQuantity;
                
                // Update item subtotal
                const itemSubtotal = document.querySelector(`.item-subtotal[data-item-id="${itemId}"]`);
                itemSubtotal.textContent = `${data.item_subtotal.toFixed(2)} ₪`;
                
                // Update cart summary
                updateCartSummary(data);
                
                // Update cart count in header
                updateCartCount(data.total_items);
            } else {
                showMessage(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('אירעה שגיאה בעדכון הכמות', 'error');
        });
    }
    
    // Remove item via AJAX
    function removeItem(itemId) {
        fetch(`/cart/remove/${itemId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove item from DOM
                const cartItem = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
                cartItem.style.transition = 'opacity 0.3s ease';
                cartItem.style.opacity = '0';
                
                setTimeout(() => {
                    cartItem.remove();
                    
                    // Update cart summary
                    updateCartSummary(data);
                    
                    // Update cart count in header
                    updateCartCount(data.total_items);
                    
                    // Check if cart is empty
                    const remainingItems = document.querySelectorAll('.cart-item');
                    if (remainingItems.length === 0) {
                        showEmptyCart();
                    }
                    
                    showMessage(data.message, 'success');
                }, 300);
            } else {
                showMessage(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('אירעה שגיאה בהסרת המוצר', 'error');
        });
    }
    
    // Update cart summary
    function updateCartSummary(data) {
        const subtotalElement = document.querySelector('.cart-subtotal');
        const shippingElement = document.querySelector('.shipping-fee');
        const totalElement = document.querySelector('.cart-total');
        
        if (subtotalElement) {
            subtotalElement.textContent = `${data.cart_subtotal.toFixed(2)} ₪`;
        }
        
        if (shippingElement) {
            if (data.cart_subtotal >= 75) {
                shippingElement.textContent = 'חינם';
            } else {
                shippingElement.textContent = `${data.shipping_fee.toFixed(2)} ₪`;
            }
        }
        
        if (totalElement) {
            totalElement.textContent = `${data.cart_total.toFixed(2)} ₪`;
        }
        
        // Update shipping notice
        const shippingNotice = document.querySelector('.shipping-notice');
        if (shippingNotice) {
            if (data.cart_subtotal >= 75 || data.cart_subtotal === 0) {
                shippingNotice.style.display = 'none';
            } else {
                shippingNotice.style.display = 'block';
                const remaining = 75 - data.cart_subtotal;
                const remainingAmount = shippingNotice.querySelector('.remaining-amount');
                if (remainingAmount) {
                    remainingAmount.textContent = `עוד ${remaining.toFixed(2)} ₪ למשלוח חינם`;
                }
            }
        }
    }
    
    // Update cart count in header
    function updateCartCount(count) {
        const cartCountElement = document.getElementById('cart-count');
        if (cartCountElement) {
            cartCountElement.textContent = count;
        }
    }
    
    // Show empty cart message
    function showEmptyCart() {
        const cartContent = document.querySelector('.cart-content');
        if (cartContent) {
            cartContent.innerHTML = `
                <div class="empty-cart">
                    <p>העגלה שלך ריקה</p>
                    <a href="/" class="btn-primary">המשך קניה</a>
                </div>
            `;
        }
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
});


