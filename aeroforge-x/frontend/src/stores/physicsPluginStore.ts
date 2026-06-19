import { create } from 'zustand';
import { physicsPluginApi } from '../api/physicsPluginApi';

interface PluginInfo {
  name: string;
  model_type: string;
  fidelity_levels: string[];
  version: string;
  loaded: boolean;
}

interface ModelState {
  position?: number[];
  velocity?: number[];
  attitude?: number[];
  angular_rate?: number[];
  soc?: number;
  soh?: number;
  temperature?: number;
  terminal_voltage?: number;
  control_output?: number[];
  autopilot_mode?: string;
}

interface CoupledSimulation {
  id: string;
  models: string[];
  status: string;
  current_step: number;
  fidelity: Record<string, string>;
}

interface PhysicsPluginStore {
  plugins: PluginInfo[];
  modelState: ModelState | null;
  coupledSimulations: CoupledSimulation[];
  selectedPlugin: PluginInfo | null;
  trajectoryData: { time: number[]; position: number[][]; attitude: number[][] };
  batteryData: { time: number[]; soc: number[]; soh: number[]; temperature: number[]; voltage: number[] };
  controlData: { time: number[]; output: number[][]; mode: string[] };
  loading: boolean;
  error: string | null;

  fetchPlugins: () => Promise<void>;
  registerPlugin: (data: any) => Promise<void>;
  hotReloadPlugin: (name: string) => Promise<void>;
  loadPlugin: (name: string) => Promise<void>;
  executeModel: (data: any) => Promise<void>;
  setModelParameters: (runtimeId: string, data: any) => Promise<void>;
  fetchModelState: (runtimeId: string) => Promise<void>;
  createCoupledSimulation: (data: any) => Promise<void>;
  stepCoupledSimulation: (simulationId: string, dt: number) => Promise<void>;
  switchFidelity: (runtimeId: string, fidelity: string) => Promise<void>;
  clearError: () => void;
}

export const usePhysicsPluginStore = create<PhysicsPluginStore>((set) => ({
  plugins: [],
  modelState: null,
  coupledSimulations: [],
  selectedPlugin: null,
  trajectoryData: { time: [], position: [], attitude: [] },
  batteryData: { time: [], soc: [], soh: [], temperature: [], voltage: [] },
  controlData: { time: [], output: [], mode: [] },
  loading: false,
  error: null,

  fetchPlugins: async () => {
    set({ loading: true, error: null });
    try {
      const data = await physicsPluginApi.discoverPlugins();
      set({ plugins: data.plugins || [], loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  registerPlugin: async (data: any) => {
    try {
      await physicsPluginApi.registerPlugin(data);
      const result = await physicsPluginApi.discoverPlugins();
      set({ plugins: result.plugins || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  hotReloadPlugin: async (name: string) => {
    try {
      await physicsPluginApi.hotReloadPlugin(name);
      const result = await physicsPluginApi.discoverPlugins();
      set({ plugins: result.plugins || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  loadPlugin: async (name: string) => {
    try {
      await physicsPluginApi.loadPlugin(name);
      const result = await physicsPluginApi.discoverPlugins();
      set({ plugins: result.plugins || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  executeModel: async (data: any) => {
    set({ loading: true, error: null });
    try {
      const result = await physicsPluginApi.executeModel(data);
      set((state) => {
        if (data.model_type === 'dof6') {
          const td = state.trajectoryData;
          return {
            trajectoryData: {
              time: [...td.time, result.time],
              position: [...td.position, result.position],
              attitude: [...td.attitude, result.attitude],
            },
            loading: false,
          };
        }
        if (data.model_type === 'battery') {
          const bd = state.batteryData;
          return {
            batteryData: {
              time: [...bd.time, result.time],
              soc: [...bd.soc, result.soc],
              soh: [...bd.soh, result.soh],
              temperature: [...bd.temperature, result.temperature],
              voltage: [...bd.voltage, result.terminal_voltage],
            },
            loading: false,
          };
        }
        if (data.model_type === 'control') {
          const cd = state.controlData;
          return {
            controlData: {
              time: [...cd.time, result.time],
              output: [...cd.output, result.control_output],
              mode: [...cd.mode, result.autopilot_mode],
            },
            loading: false,
          };
        }
        return { loading: false };
      });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  setModelParameters: async (runtimeId: string, data: any) => {
    try {
      await physicsPluginApi.setModelParameters(runtimeId, data);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchModelState: async (runtimeId: string) => {
    try {
      const data = await physicsPluginApi.getModelState(runtimeId);
      set({ modelState: data });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  createCoupledSimulation: async (data: any) => {
    try {
      const result = await physicsPluginApi.createCoupledSimulation(data);
      set((state) => ({
        coupledSimulations: [...state.coupledSimulations, result],
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  stepCoupledSimulation: async (simulationId: string, dt: number) => {
    try {
      await physicsPluginApi.stepCoupledSimulation(simulationId, dt);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  switchFidelity: async (runtimeId: string, fidelity: string) => {
    try {
      await physicsPluginApi.switchRuntimeFidelity(runtimeId, fidelity);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  clearError: () => set({ error: null }),
}));