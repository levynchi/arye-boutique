/**
 * Footer Accordion - Mobile functionality
 * Handles the accordion behavior for footer sections on mobile devices
 */

document.addEventListener('DOMContentLoaded', function() {
    const accordionToggles = document.querySelectorAll('.footer-accordion-toggle');
    
    accordionToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            const contentId = this.getAttribute('aria-controls');
            const content = document.getElementById(contentId);
            
            if (!content) return;
            
            // Toggle current section
            if (isExpanded) {
                // Close section
                this.setAttribute('aria-expanded', 'false');
                content.classList.remove('is-open');
            } else {
                // Open section
                this.setAttribute('aria-expanded', 'true');
                content.classList.add('is-open');
            }
        });
        
        // Keyboard accessibility
        toggle.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });
    
    // Reset accordion state on window resize (for switching between mobile/desktop)
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            const isMobile = window.innerWidth <= 768;
            
            if (!isMobile) {
                // Reset all accordions to closed state when switching to desktop
                accordionToggles.forEach(toggle => {
                    toggle.setAttribute('aria-expanded', 'false');
                    const contentId = toggle.getAttribute('aria-controls');
                    const content = document.getElementById(contentId);
                    if (content) {
                        content.classList.remove('is-open');
                    }
                });
            }
        }, 150);
    });
});





