ALTER TABLE stacktach_instanceexists ADD fail_reason VARCHAR(200);
CREATE INDEX `stacktach_instanceexists_fail_reason1` ON `stacktach_instanceexists` (`fail_reason`);