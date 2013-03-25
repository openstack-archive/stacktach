ALTER TABLE stacktach_instanceexists ADD fail_reason VARCHAR(500);
CREATE INDEX `stacktach_instanceexists_347f3d31` ON `stacktach_instanceexists` (`fail_reason`);
