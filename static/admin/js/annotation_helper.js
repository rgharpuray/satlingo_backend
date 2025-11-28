/**
 * Helper script for creating passage annotations in Django admin
 * Allows easy text selection and automatic character position calculation
 */

(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Find the passage content field
        const contentField = $('#id_content');
        if (!contentField.length) return;
        
        // Create annotation helper UI
        const helperHTML = `
            <div id="annotation-helper" style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                <h4>📝 Annotation Helper</h4>
                <p style="margin: 5px 0;">Select text in the passage content below, then click "Create Annotation"</p>
                <div id="selected-text-display" style="margin: 10px 0; padding: 10px; background: white; border: 1px solid #ddd; border-radius: 3px; min-height: 40px;">
                    <em style="color: #999;">No text selected. Click and drag in the passage content field above to select text.</em>
                </div>
                <button type="button" id="create-annotation-btn" class="button" style="margin-top: 10px;" disabled>
                    Create Annotation from Selection
                </button>
                <button type="button" id="clear-selection-btn" class="button" style="margin-top: 10px; margin-left: 10px;">
                    Clear Selection
                </button>
            </div>
        `;
        
        // Insert helper after content field
        contentField.after(helperHTML);
        
        let selectedText = '';
        let startChar = 0;
        let endChar = 0;
        
        // Handle text selection in content field
        contentField.on('mouseup', function() {
            const selection = window.getSelection();
            const text = selection.toString().trim();
            
            if (text.length > 0) {
                // Get the selected text and calculate positions
                const fieldValue = contentField.val();
                const range = selection.getRangeAt(0);
                
                // Calculate character positions
                // This is approximate - for textarea we need to count from start
                const textBefore = fieldValue.substring(0, fieldValue.indexOf(text));
                startChar = textBefore.length;
                endChar = startChar + text.length;
                
                selectedText = text;
                
                // Update display
                $('#selected-text-display').html(`
                    <strong>Selected Text:</strong><br>
                    <span style="background: #fff3cd; padding: 2px 4px; border-radius: 2px;">${escapeHtml(text)}</span><br>
                    <small style="color: #666;">Characters: ${startChar} to ${endChar} (length: ${text.length})</small>
                `);
                
                $('#create-annotation-btn').prop('disabled', false);
            }
        });
        
        // Create annotation button
        $('#create-annotation-btn').on('click', function() {
            if (!selectedText) return;
            
            // Find the first empty annotation inline form
            const inlineForms = $('.inline-group .form-row:not(.empty-form)');
            let targetForm = null;
            
            // Look for an empty form
            inlineForms.each(function() {
                const startCharField = $(this).find('input[name$="-start_char"]');
                if (startCharField.length && !startCharField.val()) {
                    targetForm = $(this);
                    return false; // break
                }
            });
            
            // If no empty form, add a new one
            if (!targetForm || targetForm.length === 0) {
                $('.add-row a').click();
                // Wait for form to be added
                setTimeout(function() {
                    targetForm = $('.inline-group .form-row').last();
                    fillAnnotationForm(targetForm);
                }, 100);
            } else {
                fillAnnotationForm(targetForm);
            }
        });
        
        function fillAnnotationForm(form) {
            // Find fields in the form (handle both nested and regular inlines)
            const startField = form.find('input[name$="-start_char"], input[id*="start_char"]').first();
            const endField = form.find('input[name*="-end_char"], input[id*="end_char"]').first();
            const textField = form.find('input[name*="-selected_text"], textarea[name*="-selected_text"]').first();
            const explanationField = form.find('textarea[name*="-explanation"], input[name*="-explanation"]').first();
            
            if (startField.length) startField.val(startChar);
            if (endField.length) endField.val(endChar);
            if (textField.length) textField.val(selectedText);
            
            // Focus explanation field for user to fill in
            if (explanationField.length) {
                explanationField.focus();
                explanationField.val(''); // Clear any existing value
            }
            
            // Clear selection
            clearSelection();
        }
        
        // Clear selection button
        $('#clear-selection-btn').on('click', function() {
            clearSelection();
        });
        
        function clearSelection() {
            selectedText = '';
            startChar = 0;
            endChar = 0;
            $('#selected-text-display').html('<em style="color: #999;">No text selected. Click and drag in the passage content field above to select text.</em>');
            $('#create-annotation-btn').prop('disabled', true);
            window.getSelection().removeAllRanges();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Also handle textarea selection (for content field)
        if (contentField.is('textarea')) {
            contentField.on('select', function() {
                const textarea = this;
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const text = textarea.value.substring(start, end);
                
                if (text.trim().length > 0) {
                    selectedText = text.trim();
                    startChar = start;
                    endChar = end;
                    
                    $('#selected-text-display').html(`
                        <strong>Selected Text:</strong><br>
                        <span style="background: #fff3cd; padding: 2px 4px; border-radius: 2px;">${escapeHtml(text.trim())}</span><br>
                        <small style="color: #666;">Characters: ${start} to ${end} (length: ${text.trim().length})</small>
                    `);
                    
                    $('#create-annotation-btn').prop('disabled', false);
                }
            });
        }
    });
})(django.jQuery);



