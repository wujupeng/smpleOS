import { create } from 'zustand';
import { propagationApi } from '../api/propagationApi';

interface ChainConfig {
  id: string;
  name: string;
  trigger_event: string;
  handlers: { name: string; config: any }[];
  gates: { type: string; timeout_hours: number; approvers: string[] }[];
  status: string;
}

interface ChainExecution {
  chain_id: string;
  execution_id: string;
  status: string;
  current_step: number;
  total_steps: number;
  started_at: string;
  completed_at?: string;
  handler_results: { handler: string; status: string; duration_ms: number }[];
}

interface HandlerInfo {
  name: string;
  version: string;
  input_schema: any;
  output_schema: any;
  loaded: boolean;
}

interface AuditEntry {
  id: string;
  chain_id: string;
  execution_id: string;
  handler_name: string;
  action: string;
  actor: string;
  timestamp: string;
  input_snapshot: any;
  output_snapshot: any;
  decision?: string;
}

interface PropagationStore {
  chains: ChainConfig[];
  executions: ChainExecution[];
  handlers: HandlerInfo[];
  auditLogs: AuditEntry[];
  selectedChain: ChainConfig | null;
  loading: boolean;
  error: string | null;

  fetchChains: () => Promise<void>;
  configureChain: (data: any) => Promise<void>;
  getChainStatus: (chainId: string) => Promise<void>;
  executeChain: (chainId: string, data?: any) => Promise<void>;
  fetchAuditLogs: (chainId: string) => Promise<void>;
  fetchHandlers: () => Promise<void>;
  registerHandler: (data: any) => Promise<void>;
  hotReloadHandler: (name: string) => Promise<void>;
  clearError: () => void;
}

export const usePropagationStore = create<PropagationStore>((set) => ({
  chains: [],
  executions: [],
  handlers: [],
  auditLogs: [],
  selectedChain: null,
  loading: false,
  error: null,

  fetchChains: async () => {
    set({ loading: true, error: null });
    try {
      const data = await propagationApi.listChains();
      set({ chains: data.chains || [], loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  configureChain: async (data: any) => {
    try {
      await propagationApi.configureChain(data);
      const result = await propagationApi.listChains();
      set({ chains: result.chains || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  getChainStatus: async (chainId: string) => {
    try {
      const data = await propagationApi.getChainStatus(chainId);
      set((state) => ({
        selectedChain: state.chains.find((c) => c.id === chainId) || null,
        executions: [data, ...state.executions.filter((e) => e.execution_id !== data.execution_id)],
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  executeChain: async (chainId: string, data?: any) => {
    try {
      await propagationApi.executeChain(chainId, data);
      const status = await propagationApi.getChainStatus(chainId);
      set((state) => ({
        executions: [status, ...state.executions.filter((e) => e.execution_id !== status.execution_id)],
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchAuditLogs: async (chainId: string) => {
    try {
      const data = await propagationApi.getChainAudit(chainId);
      set({ auditLogs: data.entries || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchHandlers: async () => {
    try {
      const data = await propagationApi.listHandlers();
      set({ handlers: data.handlers || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  registerHandler: async (data: any) => {
    try {
      await propagationApi.registerHandler(data);
      const result = await propagationApi.listHandlers();
      set({ handlers: result.handlers || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  hotReloadHandler: async (name: string) => {
    try {
      await propagationApi.hotReloadHandler(name);
      const result = await propagationApi.listHandlers();
      set({ handlers: result.handlers || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  clearError: () => set({ error: null }),
}));