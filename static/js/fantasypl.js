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
	/* update current formation text and good/bad indicator */
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
		/* capture status we are switching to */
		var inlineup = $(this).is(':checked');

		/* calculate ID number */
		var playerno = $(this).attr('id').replace('startercheck', '').replace('subcheck', '');

		/* set both checkboxes to the right value */
		$('#'.concat('startercheck').concat(playerno)).prop('checked', inlineup);
		$('#'.concat('subcheck').concat(playerno)).prop('checked', inlineup);

		/* collapse in/out the right table rows */
		if (inlineup) {
			$('#'.concat('starterrow').concat(playerno)).removeClass("out").addClass("in");
			$('#'.concat('subrow').concat(playerno)).removeClass("in").addClass("out");
		} else {
			$('#'.concat('starterrow').concat(playerno)).removeClass("in").addClass("out");
			$('#'.concat('subrow').concat(playerno)).removeClass("out").addClass("in");
		}
		/* reflect whether formation is valid in the interface */
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
		}
	});
}

function nextGoal(team) {
	rv = 1;
	$('.' + team + 'goal').each(function() { rv++; });
	return rv;
}

function renumberGoals(team) {
	n = 1;
	$("tr." + team + "goal").each(function() {
		$(this).attr('id', team + 'goal' + n);
		$(this).children('input[id^=' + team + 'scorer]').attr('id', team + 'scorer' + n).attr('name', team + 'scorer' + n);
		$(this).children('input[id^=' + team + 'assist]').attr('id', team + 'assist' + n).attr('name', team + 'assist' + n);
		$(this).find('.btn').unbind('click').click({team: team, n: n}, deleteGoal);
		n++;
	});
}

function deleteGoal(event) {
	$("#" + event.data.team + "goal" + event.data.n).remove();
	renumberGoals(event.data.team);
}

function addGoal(team) {
	n = nextGoal(team);

	newGoal = document.createElement('tr');
	$(newGoal).attr('id', team + 'goal' + n).addClass(team + 'goal');

	scorerCell = document.createElement('td');
	scorerDropdown = document.createElement('input');
	$(scorerDropdown).attr('id', team + 'scorer' + n).attr('name', team + 'scorer' + n).addClass('form-control').appendTo(scorerCell);
	$(scorerCell).appendTo(newGoal);

	assistCell = document.createElement('td');
	assistDropdown = document.createElement('input');
	$(assistDropdown).attr('id', team + 'assist' + n).attr('name', team + 'assist' + n).addClass('form-control').appendTo(assistCell);
	$(assistCell).appendTo(newGoal);

	deleteCell = document.createElement('td');
	deleteButton = document.createElement('span');
	$(deleteButton).html('<span class="glyphicon glyphicon-trash" aria-hidden="true">').addClass("btn").addClass("btn-sm").addClass("btn-default");
	$(deleteButton).click({team: team, n: n}, deleteGoal);
	$(deleteButton).appendTo(deleteCell);
	$(deleteCell).appendTo(newGoal);

	$(newGoal).appendTo($("#" + team + "goals"));

	if ( team == 'home' ) {
		jsonurl = JSON_HOME_PLAYERS;
	} else {
		jsonurl = JSON_AWAY_PLAYERS;
	}

	selectifyNewDropdown(scorerDropdown, "own goal", jsonurl);
	selectifyNewDropdown(assistDropdown, "no assist", jsonurl);
}

$(document).ready(function() {

	$('.startercheck').change(checkboxToggle);
	$('.subcheck').change(checkboxToggle);
	$('#addhomegoal').click(function() { addGoal("home"); });
	$('#addawaygoal').click(function() { addGoal("away"); });

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

	$('.home-player-dropdown').select2({
		allowClear: true,
		placeholder: "Select a player",
		ajax: {
			url: JSON_HOME_PLAYERS,
			data: function(term, page) {
				return { q: term };
			},
			results: function(data, page) {
				return {results: data.players};
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
				return {results: data.players};
			}
		}
	});

	$('.deadline').text(prettyDate(new Date(TIME_DEADLINE)));
	$("#priorities").val(currentOrder());

	updateFormationValidity();
});