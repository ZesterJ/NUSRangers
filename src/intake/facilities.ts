import type { Facility } from './types';

/**
 * SAMPLE facility list for the fictional Ondera catchment in the brief.
 * Replace with real facilities from healthsites.io / Kenya Master Health Facility List for the chosen
 * county, travel times from Malaria Atlas Project travel-time surfaces or AccessMod, and
 * typicalStaffPresence from World Bank Service Delivery Indicators (provider absence) for Kenya.
 * Until then, label this as sample data in the demo.
 */
const hoursAgo = (h: number) => new Date(Date.now() - h * 3600_000).toISOString();

export const SAMPLE_FACILITIES: Facility[] = [
  {
    id: 'ondera-disp',
    name: 'Ondera Dispensary (sample)',
    level: 'dispensary',
    capabilities: ['general', 'under5'],
    travelMinutes: 25,
    phone: '+254700000001',
    capacity: { staffOnDuty: 1, queue: 'long', updatedAt: hoursAgo(2) },
    typicalStaffPresence: 0.6,
  },
  {
    id: 'ondera-hc',
    name: 'Ondera Health Centre (sample)',
    level: 'health_centre',
    capabilities: ['general', 'under5', 'maternity', 'lab'],
    travelMinutes: 55,
    phone: '+254700000002',
    capacity: { staffOnDuty: 4, queue: 'medium', updatedAt: hoursAgo(5) },
    typicalStaffPresence: 0.75,
  },
  {
    id: 'kiriti-hc',
    name: 'Kiriti Health Centre (sample)',
    level: 'health_centre',
    capabilities: ['general', 'under5', 'lab'],
    travelMinutes: 40,
    phone: '+254700000003',
    capacity: null,
    typicalStaffPresence: 0.55,
  },
  {
    id: 'district-hosp',
    name: 'District Sub-County Hospital (sample)',
    level: 'sub_county_hospital',
    capabilities: ['general', 'under5', 'maternity', 'lab', 'emergency'],
    travelMinutes: 110,
    phone: '+254700000004',
    capacity: { staffOnDuty: 12, queue: 'long', updatedAt: hoursAgo(30) },
    typicalStaffPresence: 0.85,
  },
];
