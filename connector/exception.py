# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


class ConnectorException(RuntimeError):
    """ Base Exception for the connectors """


class NoConnectorUnitError(ConnectorException):
    """ No ConnectorUnit has been found """


class InvalidDataError(ConnectorException):
    """ Data Invalid """


class MappingError(ConnectorException):
    """ An error occurred during a mapping transformation. """


class JobError(ConnectorException):
    """ A job had an error """


class NoSuchJobError(JobError):
    """ The job does not exist. """


class NotReadableJobError(JobError):
    """ The job cannot be read from the storage. """


class FailedJobError(JobError):
    """ A job had an error having to be resolved. """


class RetryableJobError(JobError):
    """ A job had an error but can be retried. """


class NetworkRetryableError(RetryableJobError):
    """ A network error caused the failure of the job, it can be retried later.
    """


class NothingToDoJob(JobError):
    """ The Job has nothing to do. """


class NoExternalId(RetryableJobError):
    """ No External ID found, it can be retried later. """


class IDMissingInBackend(JobError):
    """ The ID of does not exist in the backend """


class ManyIDSInBackend(JobError):
    """Unique key exists many times in backend"""
