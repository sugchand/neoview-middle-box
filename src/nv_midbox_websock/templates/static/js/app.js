'use strict'
angular.module('landingApp', [])
.controller('landingController', ['$scope', '$window', function($scope, $window) {
  var host = "ws://" + $window.location.host + "/userwebsocket",
  ws = new WebSocket(host);
  ws.onmessage = function(e) {
    var parsed = JSON.parse(e.data);
    $scope.cameraInfo = [];
    for(var i=0;i<parsed.length;i++) {
      if(!isEmpty(parsed[i])) {
        $scope.cameraInfo[i] = parsed[i];  
      }
    }
    $scope.$apply();
  };

  $scope.changeChk = function(index, status) {
    var cameraInfo = $scope.cameraInfo[index];
    cameraInfo.status = status;
    ws.send(JSON.stringify([cameraInfo]));
    debugger;
    if(status === 1) {
      $scope.disabled = true;
    } else {
      $scope.disabled = false;
    }
  };

  function isEmpty(obj) {
    for (var prop in obj) {
      if (obj.hasOwnProperty(prop)) {
        return false;
      }
    }
    return true;
  };

}]);