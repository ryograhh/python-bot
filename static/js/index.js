// Dashboard functionality
document.addEventListener('alpine:init', () => {
    Alpine.data('dashboard', () => ({
        // State variables
        activeTab: 'users',
        users: [],
        transactions: [],
        searchTerm: '',
        isLoading: true,

        // Initialize data
        async init() {
            try {
                const [usersResponse, transactionsResponse] = await Promise.all([
                    fetch('/api/users'),
                    fetch('/api/transactions')
                ]);
                
                if (!usersResponse.ok) {
                    throw new Error('Failed to fetch users');
                }
                if (!transactionsResponse.ok) {
                    throw new Error('Failed to fetch transactions');
                }

                this.users = await usersResponse.json();
                this.transactions = await transactionsResponse.json();
                
                // Validate and clean transactions data
                this.transactions = this.transactions.filter(tx => 
                    tx && 
                    tx.user_id && 
                    tx.type && 
                    typeof tx.amount === 'number' &&
                    tx.created_at
                );

            } catch (error) {
                console.error('Error:', error);
                // Show error to user
                alert('Failed to load data. Please refresh the page.');
            } finally {
                this.isLoading = false;
            }
        },

        // Format date helper
        formatDate(dateStr) {
            if (!dateStr) return 'Never';
            try {
                return new Date(dateStr).toLocaleString();
            } catch {
                return 'Invalid Date';
            }
        },

        // Filter users based on search term
        filteredUsers() {
            if (!Array.isArray(this.users)) return [];
            const search = this.searchTerm.toLowerCase().trim();
            return this.users.filter(user => {
                if (!user || !user.username) return false;
                return user.username.toLowerCase().includes(search) || 
                       (user.user_id && user.user_id.toString().includes(search));
            });
        },

        // Filter transactions based on search term
        filteredTransactions() {
            if (!Array.isArray(this.transactions)) return [];
            const search = this.searchTerm.toLowerCase().trim();
            return this.transactions.filter(tx => {
                if (!tx || !tx.type) return false;
                const username = this.getUsernameById(tx.user_id);
                return (tx.description && tx.description.toLowerCase().includes(search)) || 
                       (tx.user_id && tx.user_id.toString().includes(search)) ||
                       (username && username.toLowerCase().includes(search));
            });
        },

        // Calculate total coins
        getTotalCoins() {
            if (!Array.isArray(this.users)) return 0;
            return this.users.reduce((sum, user) => sum + (Number(user.coins) || 0), 0);
        },

        // Get username by user ID
        getUsernameById(userId) {
            if (!userId || !Array.isArray(this.users)) return 'Unknown';
            const user = this.users.find(u => u && u.user_id === userId);
            return user ? user.username : 'Unknown';
        },

        // Get transaction type style
        getTransactionTypeStyle(type) {
            if (!type) return 'bg-gray-100 text-gray-800';
            
            const styles = {
                'daily': 'bg-green-100 text-green-800',
                'send': 'bg-blue-100 text-blue-800',
                'receive': 'bg-yellow-100 text-yellow-800',
                'admin_code': 'bg-purple-100 text-purple-800'
            };
            return styles[type.toLowerCase()] || 'bg-gray-100 text-gray-800';
        }
    }));
});