import * as Location from 'expo-location';

import type { Coordinates } from './careRouting';

/**
 * The phone's position, from GPS: no internet needed. With `ask` false it never shows a permission
 * prompt, so it can run in the middle of the visit note; it returns null unless location was already allowed.
 */
export async function currentCoordinates(ask: boolean): Promise<Coordinates | null> {
  try {
    const permission = ask ? await Location.requestForegroundPermissionsAsync() : await Location.getForegroundPermissionsAsync();
    if (!permission.granted) return null;
    // Last known position works without a data connection; fall back to a fresh GPS fix.
    const position =
      (await Location.getLastKnownPositionAsync()) ??
      (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }));
    return { latitude: position.coords.latitude, longitude: position.coords.longitude };
  } catch (e) {
    console.warn('[location] no position available', e);
    return null;
  }
}
