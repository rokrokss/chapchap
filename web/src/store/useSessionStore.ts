import { create } from 'zustand';

interface SessionStore {
  sessionId: string;
}

const useSessionStore = create<SessionStore>(() => ({
  sessionId: crypto.randomUUID(),
}));

export default useSessionStore;
