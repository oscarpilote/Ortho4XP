#pragma once

double quick_strtod(char** str,char stop) {
	char c;
	int deci=0;
        int sign=1;
	double ret=0;
	if (**str=='-') {
		sign=-1;
		(*str)++;
	}
	while ((c=*((*str)++))!=stop) {
            if (c>='0') {
		    ret*=10;
	            ret+=(c-'0');
	            deci*=10;
	    } else if (c=='.') {
		    ++deci;
	    }
	}
	if (deci) ret/=deci;
	ret*=sign;
	return ret;
}

unsigned quick_strtou(char** str,char stop) {
	char c;
	unsigned ret=0;
	while ((c=*((*str)++))!=stop) {
		ret*=10;
	        ret+=(c-'0');
	}
	return ret;
}

