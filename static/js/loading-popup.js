class LoadingPopup {
    constructor() {
        this.overlay = document.getElementById('loading-overlay');
        this.cancelButton = document.getElementById('loading-cancel-btn');
        this.isConverting = false;
        this.currentConversionId = null;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Add cancel button event listener
        this.cancelButton.addEventListener('click', () => this.cancel());
        
        // Intercept form submissions
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (form.querySelector('input[type="file"]')) {
                    e.preventDefault();
                    this.handleFormSubmit(e, form);
                }
            });
        });
    }

    async handleFormSubmit(e, form) {
        if (this.isConverting) return;
        
        // Check if skip confirmation is unchecked
        const skipConfirmation = form.querySelector('#skip_confirmation');
        if (skipConfirmation && !skipConfirmation.checked) {
            // Submit the form to the confirmation page
            form.action = '/confirm';
            form.submit();
            return;
        }
        
        this.isConverting = true;
        this.show();

        try {
            const formData = new FormData(form);
            
            // Generate and store conversion ID
            this.currentConversionId = Date.now().toString();
            formData.append('conversion_id', this.currentConversionId);
            
            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Conversion failed');

            const result = await response.json();
            
            if (result.status === 'cancelled') {
                this.showMessage('PDF conversion cancelled.');
                return;
            }

            // Redirect or update UI based on successful conversion
            window.location.href = `/?pdf_url=${encodeURIComponent(result.pdf_url)}&view_url=${encodeURIComponent(result.view_url)}`;

        } catch (error) {
            console.error('Conversion error:', error);
            this.showMessage('Error during conversion. Please try again.');
        } finally {
            this.isConverting = false;
            this.currentConversionId = null;
            this.hide();
        }
    }

    show() {
        this.overlay.classList.add('show');
    }

    hide() {
        this.overlay.classList.remove('show');
    }

    async cancel() {
        if (!this.isConverting || !this.currentConversionId) return;

        try {
            // Send cancellation request to server with conversion ID
            const response = await fetch('/cancel_conversion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Conversion-ID': this.currentConversionId
                }
            });

            if (!response.ok) throw new Error('Failed to cancel conversion');

            // Hide the popup and reset state
            this.hide();
            this.isConverting = false;
            this.currentConversionId = null;
            
            // Reset any forms
            const form = document.querySelector('form');
            if (form) form.reset();
            
            this.showMessage('PDF conversion cancelled.');

        } catch (error) {
            console.error('Cancel error:', error);
            this.showMessage('Error cancelling conversion. Please try again.');
        }
    }

    showMessage(message) {
        const notification = document.createElement('div');
        notification.className = 'alert-notification';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Force reflow
        void notification.offsetWidth;
        
        notification.classList.add('show');
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Initialize the loading popup when the document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.loadingPopup = new LoadingPopup();
}); 