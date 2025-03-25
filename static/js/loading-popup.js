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
                // Only intercept if there's a file input present
                if (form.querySelector('input[type="file"]')) {
                    e.preventDefault();
                    this.handleFormSubmit(e, form);
                }
            });
        });
    }

    async handleFormSubmit(e, form) {
        // Check the state of the "Skip file confirmation" checkbox
        const skipConfirmationCheckbox = form.querySelector('#skip_confirmation');
        const skipConfirmation = skipConfirmationCheckbox ? skipConfirmationCheckbox.checked : true;

        const formData = new FormData(form);
        // Generate and append a conversion ID
        this.currentConversionId = Date.now().toString();
        formData.append('conversion_id', this.currentConversionId);

        if (!skipConfirmation) {
            // Show a persistent overlay with a message so the user knows file tree is being built
            this.show("Building file tree, please wait...");
            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                if (result.status === 'confirm_required' && result.redirect_url) {
                    window.location.href = result.redirect_url;
                    return;
                } else {
                    throw new Error(result.message || 'Unexpected server response.');
                }
            } catch (error) {
                console.error('Redirect error:', error);
                this.showMessage('An error occurred while preparing file confirmation.');
                this.hide();
                return;
            }
        }

        // If confirmation is skipped, proceed with conversion and show the loading popup
        this.isConverting = true;
        this.show("Converting PDF, please wait...");

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) throw new Error('Conversion failed');
            const result = await response.json();
            if (result.status === 'success') {
                window.location.href = `/?pdf_url=${encodeURIComponent(result.pdf_url)}&view_url=${encodeURIComponent(result.view_url)}`;
            } else {
                throw new Error(result.message || 'PDF Conversion error.');
            }
        } catch (error) {
            console.error('Conversion error:', error);
            this.showMessage('Error during conversion. Please try again.');
        } finally {
            this.isConverting = false;
            this.currentConversionId = null;
            this.hide();
        }
    }

    // Modified show method to accept an optional message
    show(message) {
        if (message) {
            let messageElement = this.overlay.querySelector('.loading-message');
            if (!messageElement) {
                messageElement = document.createElement('div');
                messageElement.className = 'loading-message';
                this.overlay.appendChild(messageElement);
            }
            messageElement.textContent = message;
        }
        this.overlay.classList.add('show');
    }

    hide() {
        this.overlay.classList.remove('show');
        // Remove any loading message so it doesn't persist
        const messageElement = this.overlay.querySelector('.loading-message');
        if (messageElement) {
            messageElement.textContent = '';
        }
    }

    async cancel() {
        if (!this.isConverting || !this.currentConversionId) return;
        try {
            const response = await fetch('/cancel_conversion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Conversion-ID': this.currentConversionId
                }
            });
            if (!response.ok) throw new Error('Failed to cancel conversion');
            this.hide();
            this.isConverting = false;
            this.currentConversionId = null;
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
