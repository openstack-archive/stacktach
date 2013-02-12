ALTER TABLE stacktach_rawdata ADD image_type integer;
CREATE INDEX `stacktach_rawdata_cfde77eb` ON `stacktach_rawdata` (`image_type`);
