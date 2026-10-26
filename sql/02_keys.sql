-- Primary keys
ALTER TABLE customers ADD CONSTRAINT customers_pkey PRIMARY KEY (customer_id);
ALTER TABLE accounts ADD CONSTRAINT accounts_pkey PRIMARY KEY (account_id);
ALTER TABLE devices ADD CONSTRAINT devices_pkey PRIMARY KEY (device_id);
ALTER TABLE account_devices ADD CONSTRAINT account_devices_pkey PRIMARY KEY (account_id, device_id);
ALTER TABLE transfers ADD CONSTRAINT transfers_pkey PRIMARY KEY (transfer_id);

-- Foreign keys: ownership, device use, both transfer endpoints
ALTER TABLE accounts ADD CONSTRAINT accounts_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (customer_id);
ALTER TABLE account_devices ADD CONSTRAINT account_devices_account_fk FOREIGN KEY (account_id)  REFERENCES accounts (account_id);
ALTER TABLE account_devices ADD CONSTRAINT account_devices_device_fk FOREIGN KEY (device_id)   REFERENCES devices (device_id);
ALTER TABLE transfers ADD CONSTRAINT transfers_sender_fk  FOREIGN KEY (sender_id)   REFERENCES accounts (account_id);
ALTER TABLE transfers ADD CONSTRAINT transfers_receiver_fk FOREIGN KEY (receiver_id) REFERENCES accounts (account_id);