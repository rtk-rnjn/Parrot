(() => {
    'use strict';

    const { createApp } = Vue;

    createApp({
        delimiters: ['[[', ']]'],
        data() {
            return {
                loading: false,
                loadError: '',
                lastUpdated: '',
                query: '',
                commandType: 'all',
                selectedCommand: null,
                bot: { connected: false, telemetry: {} },
                commands: { ok: false, prefix: [], slash: [], default_prefix: '$' },
                cogs: [],
                extensions: [],
            };
        },
        computed: {
            allCommands() {
                return [
                    ...this.commands.prefix.map((command) => ({ ...command, kind: 'prefix' })),
                    ...this.commands.slash.map((command) => ({ ...command, kind: 'slash' })),
                ].sort((a, b) => a.name.localeCompare(b.name));
            },
            filteredCommands() {
                const needle = this.query.trim().toLowerCase();
                return this.allCommands.filter((command) => {
                    if (this.commandType !== 'all' && command.kind !== this.commandType) return false;
                    if (!needle) return true;
                    return [command.name, command.description, command.help, command.cog, ...(command.aliases || [])]
                        .filter(Boolean).join(' ').toLowerCase().includes(needle);
                });
            },
        },
        methods: {
            async refresh() {
                this.loading = true;
                this.loadError = '';
                try {
                    const response = await fetch('/api/v1/info', { headers: { Accept: 'application/json' } });
                    if (!response.ok) throw new Error(`The information endpoint returned ${response.status}.`);
                    const data = await response.json();
                    this.bot = data.bot || { connected: false, telemetry: {} };
                    this.commands = data.commands || { ok: false, prefix: [], slash: [], default_prefix: '$' };
                    this.cogs = data.cogs || [];
                    this.extensions = data.extensions || [];
                    this.selectedCommand = this.filteredCommands[0] || null;
                    this.lastUpdated = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date());
                    if (!this.bot.connected && data.ipc?.error) this.loadError = `Bot connection unavailable: ${data.ipc.error}`;
                } catch (error) {
                    this.loadError = error instanceof Error ? error.message : 'Could not load bot information.';
                } finally {
                    this.loading = false;
                }
            },
            formatNumber(value) {
                return value == null ? '—' : new Intl.NumberFormat().format(value);
            },
            formatUptime(value) {
                if (value == null) return '—';
                const days = Math.floor(value / 86400);
                const hours = Math.floor((value % 86400) / 3600);
                const minutes = Math.floor((value % 3600) / 60);
                if (days) return `${days}d ${hours}h`;
                if (hours) return `${hours}h ${minutes}m`;
                return `${minutes}m`;
            },
            usage(command) {
                if (command.kind === 'slash') return `/${command.name}${command.signature ? ` ${command.signature}` : ''}`;
                return `${this.commands.default_prefix || '{prefix}'}${command.name}${command.signature ? ` ${command.signature}` : ''}`;
            },
        },
        mounted() {
            this.refresh();
            window.setInterval(this.refresh, 30000);
        },
    }).mount('#parrot-app');
})();
