'use strict'
angular.module('landingApp', [])
.controller('landingController', ['$scope', '$window', function($scope, $window) {
  var host = "ws://" + $window.location.host + "/userwebsocket",
  ws = new WebSocket(host);
  ws.onmessage = function(e) {
    var parsed = JSON.parse(e.data);
    parsed = _.sortBy(parsed, function(obj){ return obj.name });
    $scope.cameraInfo = [];
    for(var i=0;i<parsed.length;i++) {
      if(!isEmpty(parsed[i])) {
        $scope.cameraInfo[i] = parsed[i];
      }
    }
    $scope.$apply();
  };

  $scope.changeChk = function(index, status, disableFlg) {
    if(disableFlg) {
      alert("Camera is busy, Please wait....");
    } else {
      var cameraInfo = $scope.cameraInfo[index];
      delete cameraInfo.disabled;
      cameraInfo.status = status;
      ws.send(JSON.stringify([cameraInfo]));
      $scope.cameraInfo[index].disabled = true;
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