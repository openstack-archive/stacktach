CREATE INDEX `stacktach_instanceusage_987c9676` ON `stacktach_instanceusage` (`launched_at`);
CREATE INDEX `stacktach_instancedeletes_987c9676` ON `stacktach_instancedeletes` (`launched_at`);
CREATE INDEX `stacktach_instancedeletes_738c7e64` ON `stacktach_instancedeletes` (`deleted_at`);
CREATE INDEX `stacktach_instanceexists_987c9676` ON `stacktach_instanceexists` (`launched_at`);
CREATE INDEX `stacktach_instanceexists_738c7e64` ON `stacktach_instanceexists` (`deleted_at`);
CREATE INDEX `stacktach_instanceexists_23564986` ON `stacktach_instanceexists` (`audit_period_beginning`);
CREATE INDEX `stacktach_instanceexists_b891fefb` ON `stacktach_instanceexists` (`audit_period_ending`);