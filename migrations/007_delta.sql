ALTER TABLE stacktach_instanceexists ADD send_status INTEGER;
CREATE INDEX `stacktach_instanceexists_b2444339` ON `stacktach_instanceexists` (`send_status`);