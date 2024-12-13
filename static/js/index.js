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
                const usersResponse = await fetch('/api/users');
                const transactionsResponse = await fetch('/api/transactions');
                
                if (!usersResponse.ok || !transactionsResponse.ok) {
                    throw new Error('Failed to fetch data');
                }

                this.users = await usersResponse.json();
                this.transactions = await transactionsResponse.json();
            } catch (error) {
                console.error('Error:', error);
            } finally {
                this.isLoading = false;
            }
        },

        // Format date helper
        formatDate(dateStr) {
            if (!dateStr) return 'Never';
            return new Date(dateStr).toLocaleString();
        },

        // Filter users based on search term
        filteredUsers() {
            const search = this.searchTerm.toLowerCase();
            return this.users.filter(user => {
                if (!user || !user.username) return false;
                return user.username.toLowerCase().includes(search) || 
                       (user.user_id && user.user_id.toString().includes(search));
            });
        },

        // Filter transactions based on search term
        filteredTransactions() {
            const search = this.searchTerm.toLowerCase();
            return this.transactions.filter(tx => {
                if (!tx) return false;
                return (tx.description && tx.description.toLowerCase().includes(search)) || 
                       (tx.user_id && tx.user_id.toString().includes(search));
            });
        },

        // Calculate total coins
        getTotalCoins() {
            return this.users.reduce((sum, user) => sum + (user.coins || 0), 0);
        },

        // Get username by user ID
        getUsernameById(userId) {
            const user = this.users.find(u => u.user_id === userId);
            return user ? user.username : 'Unknown';
        },

        // Get transaction type style
        getTransactionTypeStyle(type) {
            const styles = {
                'daily': 'bg-green-100 text-green-800',
                'send': 'bg-blue-100 text-blue-800',
                'receive': 'bg-yellow-100 text-yellow-800',
                'admin_code': 'bg-purple-100 text-purple-800'
            };
            return styles[type] || 'bg-gray-100 text-gray-800';
        }
    }));
});