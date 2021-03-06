## Licensed to Cloudera, Inc. under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  Cloudera, Inc. licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
<%!
from django.utils.translation import ugettext as _
%>

<%def name="render_field(field)">
  %if not field.is_hidden:
    <% group_class = len(field.errors) and "error" or "" %>
    <label class="control-label" for="id_${field.html_name}">
      <span>${field.label}</span>
      ${unicode(field) | n}
      % if len(field.errors):
        <span class="help-inline">${unicode(field.errors) | n}</span>
      % endif
      &nbsp;
    </label>
  %endif
</%def>

<form action="${path}" method="POST" class="form form-inline right">
  <div class="modal-header left">
    <button type="button" class="close" data-dismiss="modal">&times;</button>
    <h3>${_('Sync LDAP users and groups')}</h3>
  </div>
  <div class="modal-body">
    <div class="alert alert-info left">
      <p>${_("This will not import any users or groups that don't already exist in Hue. Only users and groups imported from LDAP can be synced.")}</p>
      <p>${_("All user information and group memberships will be updated based on the LDAP server's current state.")}</p>
    </div>
    % for field in form:
      ${render_field(field)}
    % endfor
  </div>
  <div class="modal-footer">
    <a href="#" class="btn" data-dismiss="modal">${_('Cancel')}</a>
    <input type="submit" class="btn primary" value="${_('Sync')}"/>
  </div>
</form>