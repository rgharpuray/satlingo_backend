/**
 * Annotation Helper - Clean SAT-style UI
 * Click-to-select interface for creating passage annotations
 */

(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Find the passage content field
        const contentField = $('#id_content');
        if (!contentField.length) return;
        
        // Create clean, professional annotation helper UI
        const helperHTML = `
            <div id="annotation-helper">
                <h4>Annotation Helper</h4>
                <p>Click once in the passage below to set the start position, then click again to set the end position.</p>
                <div id="selection-status">
                    <div id="status-message">Step 1: Click in the passage below to set the start position</div>
                    <div id="selection-info" style="display: none;">
                        <strong>Selected Text:</strong>
                        <span id="selected-text-preview"></span>
                        <span id="char-range"></span>
                    </div>
                </div>
                <div style="margin-top: 16px;">
                    <button type="button" id="create-annotation-btn" class="button" disabled>
                        Fill Annotation Form
                </button>
                    <button type="button" id="clear-selection-btn" class="button">
                    Clear Selection
                </button>
                </div>
                <div id="passage-display-container" style="margin-top: 20px;">
                    <div style="margin-bottom: 12px; font-weight: 600; color: #87CEEB; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">
                        Passage Text (Click to Select)
                    </div>
                    <div id="passage-display"></div>
                </div>
            </div>
        `;
        
        // Insert helper after content field
        contentField.after(helperHTML);
        
        // Get passage content
        let passageContent = contentField.val() || '';
        if (!passageContent.trim()) {
            $('#passage-display').html('<p style="color: #666; text-align: center; padding: 40px;">Enter passage content above to use the annotation helper.</p>');
            return;
        }
        
        // State management
        let selectionState = 'waiting-start';
        let startChar = null;
        let endChar = null;
        let selectedText = '';
        
        // Render passage with character tracking
        function renderPassage() {
            const passageDisplay = $('#passage-display');
            const content = passageContent;
            
            let html = '';
            for (let i = 0; i < content.length; i++) {
                const char = content[i];
                let displayChar = char;
                if (char === ' ') {
                    displayChar = '\u00A0';
                } else if (char === '\n') {
                    displayChar = '\n';
                } else if (char === '\t') {
                    displayChar = '\u00A0\u00A0\u00A0\u00A0';
                }
                const escapedChar = escapeHtml(displayChar);
                html += `<span class="char-pos" data-char-index="${i}">${escapedChar}</span>`;
            }
            
            passageDisplay.html(html);
            
            // Add click handlers
            passageDisplay.find('.char-pos').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const charIndex = parseInt($(this).data('char-index'));
                handleCharClick(charIndex);
            });
            
            updateHighlighting();
        }
        
        // Handle character click
        function handleCharClick(charIndex) {
            if (selectionState === 'waiting-start') {
                startChar = charIndex;
                selectionState = 'waiting-end';
                updateStatusMessage('Step 2: Click again to set the end position');
                updateHighlighting();
            } else if (selectionState === 'waiting-end') {
                if (charIndex === startChar) {
                    startChar = null;
                    selectionState = 'waiting-start';
                    updateStatusMessage('Step 1: Click in the passage below to set the start position');
                    updateHighlighting();
                    return;
                }
                
                if (charIndex < startChar) {
                    endChar = startChar;
                    startChar = charIndex;
                } else {
                    endChar = charIndex + 1;
                }
                
                selectionState = 'complete';
                selectedText = passageContent.substring(startChar, endChar);
                updateStatusMessage('Selection complete! Click "Fill Annotation Form" to populate the fields.');
                updateSelectionInfo();
                updateHighlighting();
                $('#create-annotation-btn').prop('disabled', false);
            } else if (selectionState === 'complete') {
                startChar = charIndex;
                endChar = null;
                selectionState = 'waiting-end';
                selectedText = '';
                updateStatusMessage('Step 2: Click again to set the end position');
                $('#selection-info').hide();
                $('#create-annotation-btn').prop('disabled', true);
                updateHighlighting();
            }
        }
        
        // Update highlighting
        function updateHighlighting() {
            const passageDisplay = $('#passage-display');
            passageDisplay.find('.char-pos').each(function() {
                const charIndex = parseInt($(this).data('char-index'));
                $(this).removeClass('char-start char-end char-selected');
                
                if (startChar !== null && endChar !== null) {
                    if (charIndex >= startChar && charIndex < endChar) {
                        $(this).addClass('char-selected');
                    } else if (charIndex === startChar) {
                        $(this).addClass('char-start');
                    } else if (charIndex === endChar - 1) {
                        $(this).addClass('char-end');
                    }
                } else if (startChar !== null) {
                    if (charIndex === startChar) {
                        $(this).addClass('char-start');
                    }
                }
            });
        }
        
        // Update status message
        function updateStatusMessage(message) {
            $('#status-message').text(message);
        }
        
        // Update selection info
        function updateSelectionInfo() {
            if (startChar !== null && endChar !== null) {
                $('#selected-text-preview').text(selectedText.substring(0, 100) + (selectedText.length > 100 ? '...' : ''));
                $('#char-range').html(`<br><small>Characters: ${startChar} to ${endChar} (length: ${endChar - startChar})</small>`);
                $('#selection-info').show();
            }
        }
        
        // Create annotation button
        $('#create-annotation-btn').on('click', function() {
            if (!selectedText || startChar === null || endChar === null) return;
            
            const inlineForms = $('.inline-group .form-row:not(.empty-form)');
            let targetForm = null;
            
            inlineForms.each(function() {
                const startCharField = $(this).find('input[name$="-start_char"]');
                if (startCharField.length && !startCharField.val()) {
                    targetForm = $(this);
                    return false;
                }
            });
            
            if (!targetForm || targetForm.length === 0) {
                $('.add-row a').click();
                setTimeout(function() {
                    targetForm = $('.inline-group .form-row').last();
                    fillAnnotationForm(targetForm);
                }, 100);
            } else {
                fillAnnotationForm(targetForm);
            }
        });
        
        function fillAnnotationForm(form) {
            const startField = form.find('input[name$="-start_char"], input[id*="start_char"]').first();
            const endField = form.find('input[name*="-end_char"], input[id*="end_char"]').first();
            const textField = form.find('input[name*="-selected_text"], textarea[name*="-selected_text"]').first();
            const explanationField = form.find('textarea[name*="-explanation"], input[name*="-explanation"]').first();
            
            if (startField.length) startField.val(startChar);
            if (endField.length) endField.val(endChar);
            if (textField.length) textField.val(selectedText);
            
            if (explanationField.length) {
                explanationField.focus();
                explanationField.val('');
            }
            
            clearSelection();
        }
        
        // Clear selection button
        $('#clear-selection-btn').on('click', function() {
            clearSelection();
        });
        
        function clearSelection() {
            startChar = null;
            endChar = null;
            selectedText = '';
            selectionState = 'waiting-start';
            updateStatusMessage('Step 1: Click in the passage below to set the start position');
            $('#selection-info').hide();
            $('#create-annotation-btn').prop('disabled', true);
            updateHighlighting();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Initialize
        renderPassage();
        
        // Re-render if content changes
        contentField.on('input change', function() {
            const newContent = $(this).val() || '';
            if (newContent !== passageContent && newContent.trim()) {
                passageContent = newContent;
                clearSelection();
                renderPassage();
                }
            });
    });
})(django.jQuery);
