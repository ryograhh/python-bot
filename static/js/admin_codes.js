// Wait for Alpine.js to be ready
document.addEventListener('alpine:init', () => {
    // Define the adminCodes data and functions
    Alpine.data('adminCodes', () => ({
        // State variables
        codes: [],
        showCreateModal: false,
        showUsersModal: false,
        selectedCode: null,
        newCode: {
            coins: 0,
            description: '',
            max_uses: 1
        },
        searchTerm: '',
        loading: true,
        error: null,

        // Initialize function
        init() {
            try {
                const dataScript = document.getElementById('admin-codes-data');
                if (dataScript) {
                    this.codes = JSON.parse(dataScript.textContent || '[]');
                }
                this.loading = false;
            } catch (e) {
                console.error('Error parsing initial data:', e);
                this.error = 'Error loading initial data';
                this.loading = false;
            }
        },

        // Create new code
        async createCode() {
            try {
                const response = await fetch('/api/admin/codes/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.newCode)
                });
                const data = await response.json();
                if (response.ok) {
                    this.codes.unshift(data);
                    this.showCreateModal = false;
                    this.newCode = { coins: 0, description: '', max_uses: 1 };
                } else {
                    throw new Error(data.error || 'Failed to create code');
                }
            } catch (e) {
                this.error = e.message;
                setTimeout(() => this.error = null, 3000);
            }
        },

        // Delete code
        async deleteCode(codeId) {
            const result = await Swal.fire({
                title: 'Delete Code',
                text: 'Are you sure you want to delete this code? This action cannot be undone.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc2626', // red-600
                cancelButtonColor: '#6b7280', // gray-500
                confirmButtonText: 'Yes, delete it',
                cancelButtonText: 'Cancel',
                reverseButtons: true
            });
            
            if (!result.isConfirmed) return;
            
            try {
                // Show loading state
                Swal.fire({
                    title: 'Deleting...',
                    allowOutsideClick: false,
                    showConfirmButton: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });
                
                const response = await fetch(`/api/admin/codes/${codeId}`, {
                    method: 'DELETE',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    credentials: 'same-origin'
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Remove the code from the local state
                    this.codes = this.codes.filter(code => code.code !== codeId);
                    
                    // Show success message
                    await Swal.fire({
                        title: 'Deleted!',
                        text: 'The code has been deleted successfully.',
                        icon: 'success',
                        timer: 2000,
                        showConfirmButton: false
                    });
                } else {
                    throw new Error(data.error || 'Failed to delete code');
                }
            } catch (e) {
                console.error('Error deleting code:', e);
                
                // Show error message
                await Swal.fire({
                    title: 'Error!',
                    text: e.message || 'Failed to delete code',
                    icon: 'error',
                    confirmButtonColor: '#3b82f6' // blue-500
                });
            }
        },
        
        // Show users modal
        showUsers(code) {
            this.selectedCode = code;
            this.showUsersModal = true;
        },

        // Get status color for code
        getStatusColor(code) {
            if (!code.is_active) {
                return code.status === 'fully_redeemed' ? 
                    'bg-yellow-100 text-yellow-800' : 
                    'bg-red-100 text-red-800';
            }
            return 'bg-green-100 text-green-800';
        },

        // Get status text for code
        getStatusText(code) {
            if (!code.is_active) {
                return code.status === 'fully_redeemed' ? 
                    'Fully Redeemed' : 
                    'Expired';
            }
            const uses = code.used_by ? code.used_by.length : 0;
            const maxUses = code.max_uses || 1;
            return `Active (${uses}/${maxUses})`;
        },

        // Filter codes based on search term
        filteredCodes() {
            if (!this.searchTerm) return this.codes;
            const searchLower = this.searchTerm.toLowerCase();
            return this.codes.filter(code => {
                const codeMatch = code.code ? code.code.toLowerCase().includes(searchLower) : false;
                const descMatch = code.description ? code.description.toLowerCase().includes(searchLower) : false;
                return codeMatch || descMatch;
            });
        },

        // Format date string
        formatDate(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleString();
        },

        // Get user list for code
        getUserList(code) {
            if (!code.user_details || code.user_details.length === 0) return [];
            return code.user_details;
        }
    }));
});