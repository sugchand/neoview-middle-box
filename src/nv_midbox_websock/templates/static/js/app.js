angular.module('landingApp', [])
.controller('landingController', ['$scope', '$window', function($scope, $window) {
  var host = "ws://" + $window.location.host + "/userwebsocket"
  ws = new WebSocket(host);
  ws.onmessage = function(e) {
    $scope.cameraInfo = JSON.parse(e.data);
    $scope.$apply();
  };

  $scope.changeChk = function(cameraInfo, status) {
    cameraInfo.status = status;
    ws.send(JSON.stringify([cameraInfo]));
  };
}]);