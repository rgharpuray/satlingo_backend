(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Only run on passage ingestion admin pages
        // Check if we're on the PassageIngestion admin page
        var isIngestionPage = window.location.pathname.indexOf('/admin/api/passageingestion/') !== -1;
        if (!isIngestionPage) {
            return;
        }
        
        var $form = $('form');
        // Only set up form handling if we're on add/change page (has file input)
        if ($form.length && $form.find('input[type="file"][name="file"]').length > 0) {
        
        var $submitButtons = $form.find('input[type="submit"], button[type="submit"], input[name="_save"], input[name="_addanother"], input[name="_continue"]');
        var $fileInput = $form.find('input[type="file"][name="file"]');
        var isProcessing = false;
        
        // Create loading overlay
        var $loadingOverlay = $('<div id="ingestion-loading-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 99999; text-align: center; padding-top: 20%;">' +
            '<div style="background: white; padding: 30px; border-radius: 8px; display: inline-block; max-width: 500px; margin: 0 auto;">' +
            '<div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #417690;">Processing Ingestion...</div>' +
            '<div style="margin-bottom: 20px;">' +
            '<div class="spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #417690; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto;"></div>' +
            '</div>' +
            '<div style="color: #666; font-size: 14px;">Please wait while we extract text, parse with AI, and create the passage.<br>This may take 30-60 seconds...</div>' +
            '<div style="margin-top: 15px; color: #999; font-size: 12px;">Do not close this page or refresh.</div>' +
            '</div>' +
            '</div>');
        
        // Add spinner animation
        $('<style>').text('@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }').appendTo('head');
        
        $('body').append($loadingOverlay);
        
        // Handle form submission
        $form.on('submit', function(e) {
            // Check if file is selected
            if ($fileInput.length && $fileInput[0].files.length === 0) {
                return; // Let normal validation handle this
            }
            
            // Prevent double submission
            if (isProcessing) {
                e.preventDefault();
                return false;
            }
            
            isProcessing = true;
            
            // Disable form elements
            $form.find('input, select, textarea, button').prop('disabled', true);
            $submitButtons.prop('disabled', true).css('opacity', '0.6');
            
            // Show loading overlay
            $loadingOverlay.fadeIn(300);
            
            // Allow form to submit normally - processing happens server-side
            // The overlay will stay until page reloads
        });
        
            // If page loads with status=processing, show a message and auto-refresh
            var statusField = $form.find('[name="status"]');
            if (statusField.length && statusField.val() === 'processing') {
                // Get error message (which contains progress)
                var errorField = $form.find('[name="error_message"]');
                var progressMsg = errorField.length ? errorField.val() : 'Processing...';
                
                $loadingOverlay.find('div').first().html(
                    '<div style="font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #417690;">Processing in Background</div>' +
                    '<div style="color: #666; font-size: 14px; margin-bottom: 10px;">' + progressMsg + '</div>' +
                    '<div style="color: #999; font-size: 12px;">Page will auto-refresh every 3 seconds to show progress...</div>'
                );
                $loadingOverlay.show();
                
                // Auto-refresh every 3 seconds to show progress updates
                setInterval(function() {
                    window.location.reload();
                }, 3000);
            }
        }
    });
    
    // Handle "Process Now" button clicks in list view
    window.processIngestionNow = function(ingestionId) {
        // This function can be called directly with just the ID
        var event = { preventDefault: function() {}, stopPropagation: function() {} };
        return window.processIngestionClick(event, ingestionId);
    };
    
    window.processIngestionClick = function(event, ingestionId) {
        event.preventDefault();
        event.stopPropagation();
        
        if (!confirm('Process this ingestion?\nThis will extract text and create a passage.\nProcessing happens in the background.')) {
            return false;
        }
        
        // Show loading feedback on the button
        var $button = $(event.target).closest('a');
        var originalHtml = $button.html();
        $button.html('⏳ Processing...').css({
            'pointer-events': 'none',
            'opacity': '0.6',
            'cursor': 'not-allowed'
        });
        
        // Find the changelist form
        var $changelistForm = $('#changelist-form');
        if ($changelistForm.length === 0) {
            alert('Error: Could not find form. Please refresh and try again.');
            $button.html(originalHtml).css({'pointer-events': '', 'opacity': '', 'cursor': ''});
            return false;
        }
        
        // Set the action
        $changelistForm.find('select[name="action"]').val('process_selected');
        
        // Clear existing checkboxes and check the one for this ingestion
        $changelistForm.find('input[name="_selected_action"]').prop('checked', false);
        $changelistForm.find('input[name="_selected_action"][value="' + ingestionId + '"]').prop('checked', true);
        
        // If checkbox doesn't exist, create it
        if ($changelistForm.find('input[name="_selected_action"][value="' + ingestionId + '"]').length === 0) {
            var checkbox = $('<input>', {
                type: 'checkbox',
                name: '_selected_action',
                value: ingestionId,
                checked: true,
                style: 'display: none;'
            });
            $changelistForm.append(checkbox);
        }
        
        // Show processing message
        var $messageDiv = $('<div id="processing-message" style="position: fixed; top: 20px; right: 20px; background: #417690; color: white; padding: 15px 20px; border-radius: 5px; z-index: 10000; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">' +
            '<strong>Processing Started</strong><br>' +
            '<small>Processing in background. Page will refresh in 3 seconds...</small>' +
            '</div>');
        $('body').append($messageDiv);
        
        // Submit the form
        $changelistForm.submit();
        
        // Auto-refresh after 3 seconds to show updated status
        setTimeout(function() {
            window.location.reload();
        }, 3000);
        
        return false;
    };
    
    // Handle clicks on process buttons in list view
    $(document).on('click', '.process-ingestion-btn', function(e) {
        var ingestionId = $(this).data('ingestion-id') || $(this).attr('data-ingestion-id');
        if (ingestionId) {
            window.processIngestionClick(e, ingestionId);
        }
    });
    
    // Auto-refresh list view if any items are processing
    if (window.location.pathname.indexOf('/admin/api/passageingestion/') !== -1 && 
        window.location.pathname.indexOf('/add/') === -1 && 
        window.location.pathname.indexOf('/change/') === -1) {
        // We're on the list view
        var hasProcessing = $('td:contains("Processing")').length > 0;
        if (hasProcessing) {
            // Refresh every 5 seconds to show status updates
            setTimeout(function() {
                window.location.reload();
            }, 5000);
        }
    }
})(django.jQuery);

