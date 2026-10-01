import NetInfo from '@react-native-community/netinfo';
import { create } from 'zustand';

import { getSettings, useSettings } from './settings';

type ConnectivityState = { deviceOnline: boolean };

export const useConnectivityStore = create<ConnectivityState>(() => ({ deviceOnline: true }));

let started = false;

/** Subscribe once to NetInfo. Returns an unsubscribe function. */
export function startConnectivityWatcher() {
  if (started) return () => {};
  started = true;
  const unsubscribe = NetInfo.addEventListener((state) => {
    // isInternetReachable is null while unknown — treat unknown as online.
    const online = !!state.isConnected && state.isInternetReachable !== false;
    useConnectivityStore.setState({ deviceOnline: online });
  });
  return () => {
    started = false;
    unsubscribe();
  };
}

/** Effective connectivity: device state AND the "force offline" demo switch. */
export function isOnline() {
  return useConnectivityStore.getState().deviceOnline && !getSettings().forceOffline;
}

export function useIsOnline() {
  const deviceOnline = useConnectivityStore((s) => s.deviceOnline);
  const forceOffline = useSettings((s) => s.forceOffline);
  return deviceOnline && !forceOffline;
}
