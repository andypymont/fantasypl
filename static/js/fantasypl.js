function getTeamFormation() {
	var g = 0;
	var d = 0;
	var m = 0;
	var f = 0;

	$('.starterrow.in').each(function() {
		$(this).find('.btn').each(function() {
			if ($(this).hasClass("posicon-G")) { g++; }
			if ($(this).hasClass("posicon-D")) { d++; }
			if ($(this).hasClass("posicon-M")) { m++; }
			if ($(this).hasClass("posicon-F")) { f++; }
		});
	});

	var positions = [g.toString(), d.toString(), m.toString(), f.toString()];
	return positions.join("-");
}

function validFormation(formation) {
	var validFormations = ['1-5-3-2', '1-5-4-1', '1-4-5-1', '1-4-4-2', '1-4-3-3', '1-3-5-2', '1-3-4-3']
	return (validFormations.indexOf(formation) > -1);
}

function updateFormationValidity() {
	// update current formation text and good/bad indicator
	var formation = getTeamFormation();
	$('.formation').text("Current Formation: ".concat(formation));
	if (validFormation(formation)) {
		$('#formationvalid').removeClass("out").addClass("in");
		$('#formationinvalid').removeClass("in").addClass("out");
		$('#btn-savelineup').removeClass("disabled");
	} else {
		$('#formationvalid').removeClass("in").addClass("out");
		$('#formationinvalid').removeClass("out").addClass("in");
		$('#btn-savelineup').addClass("disabled");
	}
}

function checkboxToggle() {
		// capture status we are switching to 
		var inlineup = $(this).is(':checked');

		// calculate ID number
		var playerno = $(this).attr('id').replace('startercheck', '').replace('subcheck', '');

		// set both checkboxes to the right value
		$('#'.concat('startercheck').concat(playerno)).prop('checked', inlineup);
		$('#'.concat('subcheck').concat(playerno)).prop('checked', inlineup);

		// collapse in/out the right table rows
		if (inlineup) {
			$('#'.concat('starterrow').concat(playerno)).removeClass("out").addClass("in");
			$('#'.concat('subrow').concat(playerno)).removeClass("in").addClass("out");
		} else {
			$('#'.concat('starterrow').concat(playerno)).removeClass("in").addClass("out");
			$('#'.concat('subrow').concat(playerno)).removeClass("out").addClass("in");
		}
		// reflect whether formation is valid in the interface
		updateFormationValidity();
};

function pad(v, size) {
	var s = "" + v;
	while (s.length < size) {
		s = "0" + s;
	}
	return s;
}

function prettyDate(dt) {
	var weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
	return weekdays[dt.getDay()] + " " + pad(dt.getDate(), 2) + "/" + pad(dt.getMonth() + 1, 2) + "/" + pad(dt.getFullYear(), 4) + " " 
		   + pad(dt.getHours(), 2) + ":" + pad(dt.getMinutes(), 2);
}

function addPlayerModal(playername, playerid, waiver) {
	$('#addPlayerName').text(playername);
	$('#addPlayer').val(playerid);

	if ( waiver ) {
		$('#addPlayerWaiverNotice').removeClass("out").addClass("in");
	}
	else {
		$('#addPlayerWaiverNotice').removeClass("in").addClass("out");
	}
	$('#addPlayerModal').modal('show');
}

function moveUp(row_no) {
	var row = $("tr#waiverclaimx".replace('x', row_no));
	var previous = row.prev();

	// check to see if it is a row
	if (previous.is("tr") && !(previous.hasClass("waiverclaimheadings"))) {

		// move row above previous
		row.detach();
		previous.before(row);

		// draw attention
		row.fadeIn();
	}
	// else - already at the top

	// update current ordering and enable save/cancel buttons:
	$("#priorities").val(currentOrder());
	$(".btn-waivers").removeClass("disabled");
}

function moveDown(row_no) {
	var row = $("tr#waiverclaimx".replace('x', row_no));
	var nxt = row.next();

	// check to see if it is a row
	if (nxt.is("tr")) {

		// move row beyond next
		row.detach();
		nxt.after(row);

		// draw attention
		row.fadeIn();
	}
	// else - already at the bottom

	// update current ordering and enable save/cancel buttons:
	$("#priorities").val(currentOrder());
	$(".btn-waivers").removeClass("disabled");
}

function removeRow(row_no) {
	$("tr#waiverclaimx".replace('x', row_no)).remove();
	$("#priorities").val(currentOrder());
	$(".btn-waivers").removeClass("disabled");	
}

function currentOrder() {
	var ids = [];
	$("#waiverclaims tr td.claimno").each( function() {
		ids.push($(this).text());
	});	
	return ids;
}

function getSelectedPlayers(side) {
	var vals = [];
	$('input.' + side + '-player-dropdown').each(function() {
		vals.push(parseInt($(this).select2("val"), 10));
	});
	return vals;
}

function selectifyNewDropdown(newDropdown, placeholder, jsonurl) {
	$(newDropdown).select2({
		allowClear: true,
		placeholder: placeholder,
		ajax: {
			url: jsonurl,
			data: function(term, page) {
				return { q: term };
			},
			results: function(data, page) {
				return { results: data.players };
			}
		},
		initSelection: function(element, callback) {
			var id = $(element).val();
			if (id != "") {
				$.ajax(JSON_PLAYER_BY_ID, {
					data: {id: id},
					dataType: "json"
				}).done(function(data) {
					callback(data.players[0]);
				});
			}
		}
	});
}

function deleteGoal(event) {
	$(event.data.row).remove();
	$('span#' + team + 'score').html(countGoals(team));
}

function updateScore(team) {
	$('#homescore').html(countGoals('home'));
	$('#awayscore').html(countGoals('away'));
}

function countGoals(team) {
	rv = -1;
	$('#' + team + 'goals').find('tr').each(function() { rv++; });
	return rv;
}

function configureGoalControls(goal, team) {
	if ( team == 'home' ) {
		jsonurl = JSON_HOME_PLAYERS;
	} else {
		jsonurl = JSON_AWAY_PLAYERS;
	}

	$(goal).find('.scorerdropdown').each(function() { selectifyNewDropdown(this, "own goal", jsonurl); });
	$(goal).find('.assistdropdown').each(function() { selectifyNewDropdown(this, "no assist", jsonurl); });
	$(goal).find('.btn').click({row: goal}, deleteGoal);
}

function addGoal(team) {
	// create a new table-row
	newGoal = document.createElement('tr');
	$(newGoal).addClass(team + 'goal');

	// first column: cell containing drop-down for goal scorer
	scorerCell = document.createElement('td');
	scorerDropdown = document.createElement('input');
	$(scorerDropdown).attr('name', team + 'scorer').addClass('form-control scorerdropdown').appendTo(scorerCell);
	$(scorerCell).appendTo(newGoal);

	// second column: cell containing drop-down for assist
	assistCell = document.createElement('td');
	assistDropdown = document.createElement('input');
	$(assistDropdown).attr('name', team + 'assist').addClass('form-control assistdropdown').appendTo(assistCell);
	$(assistCell).appendTo(newGoal);

	// third column: cell for button to delete this goal
	deleteCell = document.createElement('td');
	deleteButton = document.createElement('span');
	$(deleteButton).html('<span class="glyphicon glyphicon-trash" aria-hidden="true">').addClass("btn").addClass("btn-sm").addClass("btn-default");
	$(deleteButton).appendTo(deleteCell);
	$(deleteCell).appendTo(newGoal);

	// add to the relevant table and trigger function to set up the select2 dropdowns and delete button (not in here to practice DRY with pre-existing
	// goals from time of page load)
	$(newGoal).appendTo($("#" + team + "goals"));
	configureGoalControls(newGoal, team);

	// update the score at the top of the page based on the new goal
	updateScore();
}

function deleteTrade(event) {
	$(event.data.row).remove();
}

function configureTradeControls(trade) {
	$(trade).find('.teamone-dropdown').each(function() { selectifyNewDropdown(this, "Select player", JSON_TEAM1_PLAYERS); });
	$(trade).find('.teamtwo-dropdown').each(function() { selectifyNewDropdown(this, "Select player", JSON_TEAM2_PLAYERS); });
	$(trade).find('.btn').click({row: trade}, deleteTrade);
}

function addTrade() {
	// create a new table-row
	newTrade = document.createElement('tr');
	$(newTrade).addClass('trade');

	// first column: cell containing drop-down for team 1's player
	teamOneCell = document.createElement('td');
	teamOneDropdown = document.createElement('input');
	$(teamOneDropdown).attr('name', 'firstplayer').addClass('form-control teamone-dropdown').appendTo(teamOneCell);
	$(teamOneCell).appendTo(newTrade);

	// second column: cell containing drop-down for team 2's player
	teamTwoCell = document.createElement('td');
	teamTwoDropdown = document.createElement('input');
	$(teamTwoDropdown).attr('name', 'secondplayer').addClass('form-control teamtwo-dropdown').appendTo(teamTwoCell);
	$(teamTwoCell).appendTo(newTrade);

	// third column: cell for button to delete this line
	deleteCell = document.createElement('td');
	deleteButton = document.createElement('span');
	$(deleteButton).html('<span class="glyphicon glyphicon-trash" aria-hidden="true">').addClass("btn").addClass("btn-sm").addClass("btn-default");
	$(deleteButton).appendTo(deleteCell);
	$(deleteCell).appendTo(newTrade);

	// add to the table and trigger function to set up the select2 dropdowns and delete button
	$(newTrade).appendTo($("#trades"));
	configureTradeControls(newTrade);
}

$(document).ready(function() {

	if (PAGENAME == 'lineup') {
		$('.startercheck').change(checkboxToggle);
		$('.subcheck').change(checkboxToggle);
		$('.deadline').text(prettyDate(new Date(TIME_DEADLINE)));
		$("#priorities").val(currentOrder());

		updateFormationValidity();
	}

	if (PAGENAME == 'players') {
		$('.player-dropdown').select2({
			placeholder: "Select a player",
			ajax: {
				url: JSON_TEAM_PLAYERS,
				data: function(term, page) {
					return { q: term };
				},
				results: function(data, page) {
					return {results: data.players};
				}
			}
		});
	}

	if (PAGENAME == 'trade') {
		$('#addtrade').click(function() { addTrade(); });
	}

	if (PAGENAME == 'scoring') {
		$('.position-dropdown').select2();
		$('.club-dropdown').select2();
		$('.team-dropdown').select2();

		$('.all-players-dropdown').select2({
			allowClear: true,
			placeholder: "Select a player",
			ajax: {
				url: JSON_ALL_PLAYERS,
				data: function(term, page) {
					return { q: term };
				},
				results: function(data, page) {
					return { results: data.players };
				}
			}
		});
	}

	if (PAGENAME == 'scorefixture') {

		$('#addhomegoal').click(function() { addGoal("home"); });
		$('#addawaygoal').click(function() { addGoal("away"); });

		$('tr.homegoal').each(function() { configureGoalControls(this, 'home'); });
		$('tr.awaygoal').each(function() { configureGoalControls(this, 'away'); });

		$('.home-player-dropdown').select2({
			allowClear: true,
			placeholder: "Select a player",
			ajax: {
				url: JSON_HOME_PLAYERS,
				data: function(term, page) {
					return { q: term };
				},
				results: function(data, page) {
					var results = data.players;
					var alreadypicked = getSelectedPlayers('home');

					for ( var i=0; i<results.length; i++ ) {
						if ( $.inArray(results[i].id, alreadypicked) > -1 ) {
							results[i].disabled = true;
						};
					};

					return {results: results};
				}
			},
			initSelection: function(element, callback) {
				var id = $(element).val();
				if (id != "") {
					$.ajax(JSON_PLAYER_BY_ID, {
						data: {id: id},
						dataType: "json"
					}).done(function(data) {
						callback(data.players[0]);
					});
				}
			}
		});

		$('.away-player-dropdown').select2({
			allowClear: true,
			placeholder: "Select a player",
			ajax: {
				url: JSON_AWAY_PLAYERS,
				data: function(term, page) {
					return { q: term };
				},
				results: function(data, page) {
					var results = data.players;
					var alreadypicked = getSelectedPlayers('away');

					for ( var i=0; i<results.length; i++ ) {
						if ( $.inArray(results[i].id, alreadypicked) > -1 ) {
							results[i].disabled = true;
						};
					};

					return {results: results};
				}
			},
			initSelection: function(element, callback) {
				var id = $(element).val();
				if (id != "") {
					$.ajax(JSON_PLAYER_BY_ID, {
						data: {id: id},
						dataType: "json"
					}).done(function(data) {
						callback(data.players[0]);
					});
				}
			}
		});

	}

});