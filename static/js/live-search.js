/**
 * Live Search - חיפוש חי עם autocomplete
 */
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('header-search');
    const searchDropdown = document.getElementById('search-results-dropdown');
    
    if (!searchInput || !searchDropdown) return;
    
    let debounceTimer;
    let selectedIndex = -1;

    // Escape text before placing it inside innerHTML
    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Debounce function - מונע קריאות API רבות מדי
    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }
    
    // פונקציה לביצוע חיפוש
    async function performSearch(query) {
        if (query.length < 2) {
            hideDropdown();
            return;
        }
        
        try {
            const response = await fetch(`/search/api/?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                showResults(data.results, query);
            } else {
                showNoResults(query);
            }
        } catch (error) {
            console.error('Search error:', error);
            hideDropdown();
        }
    }
    
    // הצגת תוצאות
    function showResults(results, query) {
        selectedIndex = -1;
        
        const html = results.map((product, index) => `
            <a href="/product/${encodeURIComponent(product.slug)}/" class="search-dropdown-item" data-index="${index}">
                <div class="search-item-image">
                    ${product.image ? `<img src="${escapeHtml(product.image)}" alt="">`: '<div class="search-item-no-image"></div>'}
                </div>
                <div class="search-item-info">
                    <span class="search-item-name">${highlightMatch(product.name, query)}</span>
                    ${product.subtitle ? `<span class="search-item-subtitle">${escapeHtml(product.subtitle)}</span>` : ''}
                    <span class="search-item-price">${escapeHtml(product.price)} ש"ח</span>
                </div>
            </a>
        `).join('');
        
        searchDropdown.innerHTML = html + `
            <a href="/search/?q=${encodeURIComponent(query)}" class="search-dropdown-all">
                הצג את כל התוצאות עבור "${escapeHtml(query)}"
            </a>
        `;
        
        searchDropdown.classList.add('active');
    }
    
    // הדגשת הטקסט התואם
    function highlightMatch(text, query) {
        // מפצלים לפי ההתאמות ומבצעים escape לכל חלק בנפרד
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return String(text).split(regex).map((part, index) => (
            index % 2 === 1 ? `<strong>${escapeHtml(part)}</strong>` : escapeHtml(part)
        )).join('');
    }
    
    // Escape special regex characters
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // הצגת הודעה כשאין תוצאות
    function showNoResults(query) {
        selectedIndex = -1;
        searchDropdown.innerHTML = `
            <div class="search-dropdown-empty">
                לא נמצאו תוצאות עבור "${escapeHtml(query)}"
            </div>
            <a href="/search/?q=${encodeURIComponent(query)}" class="search-dropdown-all">
                חפש בכל האתר
            </a>
        `;
        searchDropdown.classList.add('active');
    }
    
    // הסתרת dropdown
    function hideDropdown() {
        searchDropdown.classList.remove('active');
        selectedIndex = -1;
    }
    
    // ניווט מקלדת
    function handleKeyDown(e) {
        const items = searchDropdown.querySelectorAll('.search-dropdown-item');
        
        if (!searchDropdown.classList.contains('active') || items.length === 0) {
            return;
        }
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                updateSelection(items);
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateSelection(items);
                break;
                
            case 'Enter':
                if (selectedIndex >= 0 && items[selectedIndex]) {
                    e.preventDefault();
                    items[selectedIndex].click();
                }
                break;
                
            case 'Escape':
                hideDropdown();
                searchInput.blur();
                break;
        }
    }
    
    // עדכון בחירה ויזואלית
    function updateSelection(items) {
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === selectedIndex);
        });
        
        // גלילה לפריט הנבחר
        if (selectedIndex >= 0 && items[selectedIndex]) {
            items[selectedIndex].scrollIntoView({ block: 'nearest' });
        }
    }
    
    // האזנה לאירועי קלט
    searchInput.addEventListener('input', debounce(function(e) {
        const query = e.target.value.trim();
        performSearch(query);
    }, 300));
    
    // האזנה למקלדת
    searchInput.addEventListener('keydown', handleKeyDown);
    
    // סגירה בלחיצה מחוץ ל-dropdown
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
            hideDropdown();
        }
    });
    
    // הצגת dropdown בפוקוס אם יש ערך
    searchInput.addEventListener('focus', function() {
        const query = searchInput.value.trim();
        if (query.length >= 2) {
            performSearch(query);
        }
    });
});
















