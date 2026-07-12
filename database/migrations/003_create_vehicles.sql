-- Vehicles and vehicle history tracked by LifePilot Admin.
-- Target database: PostgreSQL.

CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    version TEXT,
    registration_masked TEXT,
    vin_hash TEXT,
    first_registration_date DATE,
    mileage_current INTEGER CHECK (mileage_current IS NULL OR mileage_current >= 0),
    mileage_updated_at TIMESTAMPTZ,
    technical_inspection_due_date DATE,
    insurance_contract_id UUID REFERENCES contracts(id) ON DELETE SET NULL,
    maintenance_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE vehicle_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'technical_inspection',
        'maintenance',
        'oil_change',
        'brakes',
        'tires',
        'insurance',
        'repair',
        'fuel',
        'other'
    )),
    event_date DATE NOT NULL,
    mileage INTEGER CHECK (mileage IS NULL OR mileage >= 0),
    title TEXT NOT NULL,
    description TEXT,
    cost NUMERIC(18, 2),
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    next_due_date DATE,
    next_due_mileage INTEGER CHECK (next_due_mileage IS NULL OR next_due_mileage >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vehicles_user_id ON vehicles(user_id);
CREATE INDEX idx_vehicles_insurance_contract_id ON vehicles(insurance_contract_id);
CREATE INDEX idx_vehicles_technical_inspection_due_date ON vehicles(technical_inspection_due_date);
CREATE INDEX idx_vehicle_events_vehicle_id ON vehicle_events(vehicle_id);
CREATE INDEX idx_vehicle_events_document_id ON vehicle_events(document_id);
CREATE INDEX idx_vehicle_events_event_date ON vehicle_events(event_date);
CREATE INDEX idx_vehicle_events_next_due_date ON vehicle_events(next_due_date);
