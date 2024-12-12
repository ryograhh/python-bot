// Add error notification display time
const ERROR_DISPLAY_DURATION = 3000; // 3 seconds

Alpine.data('adminCodes', () => ({
    // Add error display component
    errorMessage: null,
    showError(message) {
        this.errorMessage = message;
        setTimeout(() => this.errorMessage = null, ERROR_DISPLAY_DURATION);
    },

    // Improve error handling in fetchCodes
    async fetchCodes() {
        this.loading = true;
        try {
            const response = await fetch('/api/admin/codes');
            if (!response.ok) {
                throw new Error(`Failed to fetch codes: ${response.statusText}`);
            }
            const data = await response.json();
            this.codes = data;
        } catch (e) {
            this.showError(e.message);
        } finally {
            this.loading = false;
        }
    },

    // Improve createCode validation
    async createCode() {
        if (this.newCode.coins < 0) {
            this.showError('Coins amount cannot be negative');
            return;
        }
        if (this.newCode.max_uses < 1) {
            this.showError('Maximum uses must be at least 1');
            return;
        }

        try {
            const response = await fetch('/api/admin/codes/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]')?.content
                },
                body: JSON.stringify(this.newCode)
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to create code');
            }
            this.codes.unshift(data);
            this.showCreateModal = false;
            this.newCode = { coins: 0, description: '', max_uses: 1 };
        } catch (e) {
            this.showError(e.message);
        }
    },

    // Improve deleteCode error handling
    async deleteCode(codeId) {
        if (!codeId) {
            this.showError('Invalid code ID');
            return;
        }
        
        if (!confirm('Are you sure you want to delete this code?')) return;
        
        try {
            const response = await fetch(`/api/admin/codes/${codeId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]')?.content
                }
            });
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to delete code');
            }
            this.codes = this.codes.filter(code => code.code !== codeId);
        } catch (e) {
            this.showError(e.message);
        }
    },

    // Improve filteredCodes performance
    filteredCodes() {
        if (!this.searchTerm?.trim()) return this.codes;
        const searchLower = this.searchTerm.toLowerCase().trim();
        return this.codes.filter(code => 
            (code.code?.toLowerCase().includes(searchLower)) ||
            (code.description?.toLowerCase().includes(searchLower))
        );
    },

    // Add date validation
    formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        try {
            return new Date(dateStr).toLocaleString();
        } catch {
            return 'Invalid Date';
        }
    }
}));