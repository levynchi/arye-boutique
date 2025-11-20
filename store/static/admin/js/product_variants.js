(function($) {
    $(document).ready(function() {
        // טיפול בכפתור "צור וריאנטים" למוצר חדש
        var createVariantsBtn = $('#create-variants-btn');
        
        if (createVariantsBtn.length) {
            createVariantsBtn.on('click', function(e) {
                e.preventDefault();
                
                // מציאת הטופס - נסה כמה אפשרויות
                var form = $('form#product_form');
                if (!form.length) {
                    form = $('form[name="product_form"]');
                }
                if (!form.length) {
                    form = $('#content-main form').first();
                }
                if (!form.length) {
                    form = $('form').filter(function() {
                        return $(this).find('input[name^="name"]').length > 0;
                    }).first();
                }
                
                if (form.length) {
                    // מחיקת hidden input קיים אם יש
                    form.find('input[name="_continue_to_variants"]').remove();
                    
                    // הוספת hidden input שמסמן שצריך להמשיך ליצירת וריאנטים
                    $('<input>').attr({
                        type: 'hidden',
                        name: '_continue_to_variants',
                        value: '1'
                    }).appendTo(form);
                    
                    // שליחת הטופס
                    form.submit();
                } else {
                    alert('לא ניתן למצוא את טופס המוצר. אנא שמור את המוצר תחילה ואז השתמש בכפתור.');
                }
            });
        }
    });
})(django.jQuery);

