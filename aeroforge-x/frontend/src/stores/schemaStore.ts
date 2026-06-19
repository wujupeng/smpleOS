import { create } from 'zustand';
import { schemaApi } from '../api/schemaApi';

interface SchemaField {
  field_path: string;
  data_type: string;
  unit: string;
  required: boolean;
  default_value?: any;
  constraints?: any;
}

interface SchemaInfo {
  schema_type: string;
  version: number;
  status: string;
  fields: SchemaField[];
  created_at: string;
  updated_at: string;
}

interface MigrationResult {
  total: number;
  succeeded: number;
  failed: number;
  failures: { object_id: string; error: string }[];
}

interface UnitInfo {
  dimension: string;
  units: string[];
}

interface AttributeNameInfo {
  canonical_name: string;
  aliases: string[];
  dimension: string;
  canonical_unit: string;
}

interface SchemaStore {
  schemas: SchemaInfo[];
  selectedSchema: SchemaInfo | null;
  migrationResult: MigrationResult | null;
  supportedUnits: UnitInfo[];
  attributeNames: AttributeNameInfo[];
  loading: boolean;
  error: string | null;

  fetchSchemas: () => Promise<void>;
  selectSchema: (schemaType: string) => Promise<void>;
  publishVersion: (schemaType: string, version: number) => Promise<void>;
  deprecateVersion: (schemaType: string, version: number) => Promise<void>;
  executeMigration: (schemaType: string, data: any) => Promise<void>;
  batchMigrate: (data: any) => Promise<void>;
  fetchSupportedUnits: (dimension?: string) => Promise<void>;
  convertUnit: (value: number, fromUnit: string, toUnit: string) => Promise<number>;
  resolveAttributeName: (name: string) => Promise<AttributeNameInfo | null>;
  clearError: () => void;
}

export const useSchemaStore = create<SchemaStore>((set) => ({
  schemas: [],
  selectedSchema: null,
  migrationResult: null,
  supportedUnits: [],
  attributeNames: [],
  loading: false,
  error: null,

  fetchSchemas: async () => {
    set({ loading: true, error: null });
    try {
      const data = await schemaApi.listSchemas();
      set({ schemas: data.schemas || [], loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  selectSchema: async (schemaType: string) => {
    set({ loading: true, error: null });
    try {
      const data = await schemaApi.getSchema(schemaType);
      set({ selectedSchema: data, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  publishVersion: async (schemaType: string, version: number) => {
    try {
      await schemaApi.publishSchemaVersion(schemaType, version);
      const data = await schemaApi.getSchema(schemaType);
      set({ selectedSchema: data });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  deprecateVersion: async (schemaType: string, version: number) => {
    try {
      await schemaApi.deprecateSchemaVersion(schemaType, version);
      const data = await schemaApi.getSchema(schemaType);
      set({ selectedSchema: data });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  executeMigration: async (schemaType: string, data: any) => {
    set({ loading: true, error: null });
    try {
      const result = await schemaApi.executeMigration(schemaType, data);
      set({ migrationResult: result, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  batchMigrate: async (data: any) => {
    set({ loading: true, error: null });
    try {
      const result = await schemaApi.batchMigrate(data);
      set({ migrationResult: result, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchSupportedUnits: async (dimension?: string) => {
    try {
      const data = await schemaApi.getSupportedUnits(dimension);
      set({ supportedUnits: data.dimensions || [] });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  convertUnit: async (value: number, fromUnit: string, toUnit: string) => {
    const data = await schemaApi.convertUnit(value, fromUnit, toUnit);
    return data.converted_value;
  },

  resolveAttributeName: async (name: string) => {
    try {
      const data = await schemaApi.resolveAttributeName(name);
      return data;
    } catch {
      return null;
    }
  },

  clearError: () => set({ error: null }),
}));