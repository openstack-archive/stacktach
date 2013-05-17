ALTER TABLE stacktach_instanceexists ADD `tenant` varchar(50);
CREATE INDEX `stacktach_instanceexists_1384d482` ON `stacktach_instanceexists` (`tenant`);

ALTER TABLE stacktach_instanceusage ADD `tenant` varchar(50);
CREATE INDEX `stacktach_instanceusage_1384d482` ON `stacktach_instanceusage` (`tenant`);

