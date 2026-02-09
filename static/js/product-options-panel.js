// Product Options Panel - Quick Add to Cart from Category Pages

document.addEventListener('DOMContentLoaded', function() {
    const panel = document.getElementById('product-options-panel');
    const overlay = document.getElementById('product-options-overlay');
    const closeBtn = document.getElementById('product-options-close');
    const addBtn = document.getElementById('product-options-add-btn');
    
    // Panel elements
    const productImg = document.getElementById('product-options-img');
    const productName = document.getElementById('product-options-name');
    const productSubtitle = document.getElementById('product-options-subtitle');
    const productPrice = document.getElementById('product-options-price');
    const fabricSection = document.getElementById('product-options-fabric-section');
    const fabricsContainer = document.getElementById('product-options-fabrics');
    const sizeSection = document.getElementById('product-options-size-section');
    const sizesContainer = document.getElementById('product-options-sizes');
    const noteSection = document.getElementById('product-options-note');
    const qtyInput = document.getElementById('product-options-qty-input');
    const qtyMinus = document.getElementById('product-options-qty-minus');
    const qtyPlus = document.getElementById('product-options-qty-plus');
    
    // State
    let currentProductId = null;
    let currentProductData = null;
    let selectedFabricId = null;
    let selectedVariantId = null;
    let maxQuantity = 999;
    
    // Focus trap elements
    const focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';
    let lastFocusedElement = null;
    
    // Open panel
    function openPanel(productId) {
        lastFocusedElement = document.activeElement;
        currentProductId = productId;
        
        // Reset state
        selectedFabricId = null;
        selectedVariantId = null;
        qtyInput.value = 1;
        addBtn.disabled = true;
        addBtn.textContent = 'בחר מידה';
        
        // Fetch product data
        fetchProductData(productId);
        
        // Show panel
        panel.classList.add('active');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        panel.setAttribute('aria-hidden', 'false');
        overlay.setAttribute('aria-hidden', 'false');
        
        // Focus management
        panel.addEventListener('keydown', trapFocus);
        setTimeout(() => focusFirstElement(), 100);
    }
    
    // Close panel
    function closePanel() {
        panel.classList.remove('active');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
        panel.setAttribute('aria-hidden', 'true');
        overlay.setAttribute('aria-hidden', 'true');
        panel.removeEventListener('keydown', trapFocus);
        
        if (lastFocusedElement) {
            lastFocusedElement.focus();
            lastFocusedElement = null;
        }
        
        // Reset state
        currentProductId = null;
        currentProductData = null;
    }
    
    // Fetch product data from API
    function fetchProductData(productId) {
        fetch(`/product/${productId}/variants/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentProductData = data;
                    renderProductInfo(data.product);
                    renderVariantOptions(data);
                }
            })
            .catch(error => {
                console.error('Error fetching product data:', error);
            });
    }
    
    // Render product info
    function renderProductInfo(product) {
        productImg.src = product.image;
        productImg.alt = product.name;
        productName.textContent = product.name;
        productSubtitle.textContent = product.subtitle || '';
        productPrice.textContent = product.price.toFixed(2) + ' ₪';
        maxQuantity = product.stock_quantity;
    }
    
    // Render variant options
    function renderVariantOptions(data) {
        const fabrics = data.fabrics;
        
        if (!data.has_variants) {
            // No variants - can add directly
            fabricSection.style.display = 'none';
            sizeSection.style.display = 'none';
            noteSection.style.display = 'none';
            addBtn.disabled = false;
            addBtn.textContent = 'הוספה להזמנה';
            return;
        }
        
        // Check if multiple fabrics
        if (fabrics.length > 1) {
            // Show fabric selection
            fabricSection.style.display = 'block';
            fabricsContainer.innerHTML = '';
            
            fabrics.forEach(fabric => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'product-options-btn';
                btn.textContent = fabric.name;
                btn.dataset.fabricId = fabric.id;
                btn.addEventListener('click', () => selectFabric(fabric.id));
                fabricsContainer.appendChild(btn);
            });
            
            // Hide sizes until fabric is selected
            sizeSection.style.display = 'none';
            sizesContainer.innerHTML = '<p style="color: #666; font-size: 13px;">יש לבחור סוג בד קודם</p>';
        } else if (fabrics.length === 1) {
            // Single fabric - hide fabric section and show sizes directly
            fabricSection.style.display = 'none';
            selectedFabricId = fabrics[0].id;
            renderSizes(fabrics[0].sizes);
        } else {
            // No variants available
            fabricSection.style.display = 'none';
            sizeSection.style.display = 'none';
            addBtn.disabled = true;
            addBtn.textContent = 'לא זמין';
        }
        
        // Show note section (optional based on product type)
        noteSection.style.display = 'none'; // Can be shown for specific categories
    }
    
    // Select fabric
    function selectFabric(fabricId) {
        selectedFabricId = fabricId;
        selectedVariantId = null;
        
        // Update fabric buttons
        fabricsContainer.querySelectorAll('.product-options-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.fabricId == fabricId);
        });
        
        // Get sizes for this fabric
        const fabric = currentProductData.fabrics.find(f => f.id == fabricId);
        if (fabric) {
            renderSizes(fabric.sizes);
        }
        
        // Reset price to base and add button
        if (currentProductData && currentProductData.product && productPrice) {
            productPrice.textContent = currentProductData.product.price.toFixed(2) + ' ₪';
        }
        addBtn.disabled = true;
        addBtn.textContent = 'בחר מידה';
    }
    
    // Render sizes
    function renderSizes(sizes) {
        sizeSection.style.display = 'block';
        sizesContainer.innerHTML = '';
        
        if (sizes.length === 0) {
            sizesContainer.innerHTML = '<p style="color: #666; font-size: 13px;">אין מידות זמינות</p>';
            return;
        }
        
        sizes.forEach(sizeData => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'product-options-btn';
            btn.textContent = sizeData.size_display || sizeData.size;
            btn.dataset.variantId = sizeData.id;
            if (sizeData.price != null) btn.dataset.price = sizeData.price;
            btn.addEventListener('click', () => selectSize(sizeData.id, sizeData.price));
            sizesContainer.appendChild(btn);
        });
    }
    
    // Select size
    function selectSize(variantId, variantPrice) {
        selectedVariantId = variantId;
        
        // Update size buttons
        sizesContainer.querySelectorAll('.product-options-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.variantId == variantId);
        });
        
        // Update displayed price if variant has its own price
        if (productPrice && currentProductData && currentProductData.product) {
            const basePrice = currentProductData.product.price;
            const price = (variantPrice != null && variantPrice !== basePrice) ? variantPrice : basePrice;
            productPrice.textContent = Number(price).toFixed(2) + ' ₪';
        }
        
        // Enable add button
        addBtn.disabled = false;
        addBtn.textContent = 'הוספה להזמנה';
    }
    
    // Quantity controls
    if (qtyMinus) {
        qtyMinus.addEventListener('click', function() {
            let current = parseInt(qtyInput.value) || 1;
            if (current > 1) {
                qtyInput.value = current - 1;
            }
        });
    }
    
    if (qtyPlus) {
        qtyPlus.addEventListener('click', function() {
            let current = parseInt(qtyInput.value) || 1;
            if (current < maxQuantity) {
                qtyInput.value = current + 1;
            }
        });
    }
    
    // Add to cart
    function addToCart() {
        if (!currentProductId) return;
        
        const quantity = parseInt(qtyInput.value) || 1;
        
        const formData = new FormData();
        formData.append('quantity', quantity);
        if (selectedVariantId) {
            formData.append('variant_id', selectedVariantId);
        }
        
        // Get CSRF token
        const csrfToken = getCookie('csrftoken');
        
        addBtn.disabled = true;
        addBtn.textContent = 'מוסיף...';
        
        fetch(`/cart/add/${currentProductId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Close panel
                closePanel();
                
                // Open cart sidebar
                if (typeof window.openCartSidebar === 'function') {
                    window.openCartSidebar();
                }
                
                // Update cart count in header
                const cartCount = document.getElementById('cart-count');
                if (cartCount && data.cart_count !== undefined) {
                    cartCount.textContent = data.cart_count;
                }
            } else {
                addBtn.disabled = false;
                addBtn.textContent = 'הוספה להזמנה';
                alert(data.error || 'אירעה שגיאה בהוספת המוצר לעגלה');
            }
        })
        .catch(error => {
            console.error('Error adding to cart:', error);
            addBtn.disabled = false;
            addBtn.textContent = 'הוספה להזמנה';
            alert('אירעה שגיאה בהוספת המוצר לעגלה');
        });
    }
    
    // Focus trap
    function getFocusableElements() {
        return panel.querySelectorAll(focusableSelectors);
    }
    
    function focusFirstElement() {
        const focusableElements = getFocusableElements();
        if (focusableElements.length > 0) {
            focusableElements[0].focus();
        }
    }
    
    function trapFocus(event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            closePanel();
            return;
        }
        
        if (event.key !== 'Tab') return;
        
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
    if (closeBtn) {
        closeBtn.addEventListener('click', closePanel);
    }
    
    if (overlay) {
        overlay.addEventListener('click', closePanel);
    }
    
    if (addBtn) {
        addBtn.addEventListener('click', addToCart);
    }
    
    // Quick add button click handlers
    document.addEventListener('click', function(e) {
        const quickAddBtn = e.target.closest('.product-card-quick-add');
        if (quickAddBtn) {
            e.preventDefault();
            e.stopPropagation();
            const productId = quickAddBtn.dataset.productId;
            if (productId) {
                openPanel(productId);
            }
        }
    });
    
    // Make openPanel globally accessible if needed
    window.openProductOptionsPanel = openPanel;
});

