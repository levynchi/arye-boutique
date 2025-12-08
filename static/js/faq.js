document.addEventListener('DOMContentLoaded', function() {
    const faqQuestions = document.querySelectorAll('.faq-question');
    
    faqQuestions.forEach(question => {
        question.addEventListener('click', function() {
            const faqItem = this.parentElement;
            const answer = this.nextElementSibling;
            const icon = this.querySelector('.faq-icon');
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            
            // סגירת כל השאלות האחרות
            faqQuestions.forEach(otherQuestion => {
                if (otherQuestion !== this) {
                    otherQuestion.setAttribute('aria-expanded', 'false');
                    otherQuestion.nextElementSibling.hidden = true;
                    otherQuestion.querySelector('.faq-icon').textContent = '+';
                    otherQuestion.parentElement.classList.remove('active');
                }
            });
            
            // פתיחה/סגירה של השאלה הנוכחית
            if (isExpanded) {
                this.setAttribute('aria-expanded', 'false');
                answer.hidden = true;
                icon.textContent = '+';
                faqItem.classList.remove('active');
            } else {
                this.setAttribute('aria-expanded', 'true');
                answer.hidden = false;
                icon.textContent = '−';
                faqItem.classList.add('active');
            }
        });
    });
});
